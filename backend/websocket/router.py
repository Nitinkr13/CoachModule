import asyncio
import json
import logging
import os
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.store import append_session_turn, get_session

router = APIRouter(prefix="/ws", tags=["websocket"])
logger = logging.getLogger("coachmodule.websocket")

GEMINI_WS_URL = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
    "?key={api_key}"
)


@dataclass
class LiveSessionBuffers:
    current_input: str = ""
    current_output: str = ""
    last_input: str = ""
    last_output: str = ""


def _merge_transcript(current: str, incoming: str) -> str:
    if not incoming:
        return current
    if incoming.startswith(current):
        return incoming
    if current.startswith(incoming):
        return current
    return current + incoming


from typing import Any
import os

def _build_gemini_config(payload: dict, system_instruction: str) -> dict:
    model = payload.get(
        "model",
        os.getenv("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")
    )

    response_modalities = payload.get("responseModalities") or ["AUDIO"]

    voice_name = payload.get("voiceName", "Kore")
    language_code = payload.get("languageCode", "en-IN")

    config: dict[str, Any] = {
        "model": f"models/{model}",
        "generationConfig": {
            "responseModalities": response_modalities,

            # TTS settings
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice_name
                    }
                },

                # language/accent
                "languageCode": language_code
            },
        },

        "inputAudioTranscription": {},
        "outputAudioTranscription": {},
    }

    if system_instruction:
        config["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    return {"setup": config}


async def _send_error(websocket: WebSocket, message: str) -> None:
    logger.error("Live API error: %s", message)
    await websocket.send_text(
        json.dumps({"type": "error", "payload": {"message": message}})
    )


async def _receive_initial_config(websocket: WebSocket) -> dict | None:
    try:
        raw = await websocket.receive_text()
    except WebSocketDisconnect:
        return None

    try:
        message = json.loads(raw)
    except json.JSONDecodeError:
        await _send_error(websocket, "Invalid JSON for config message.")
        return None

    if message.get("type") != "config":
        await _send_error(websocket, "Expected config message as first payload.")
        return None

    payload = message.get("payload") or {}
    if not payload.get("sessionId"):
        await _send_error(websocket, "Missing sessionId in config payload.")
        return None

    return payload


async def _forward_client_to_gemini(
    client_ws: WebSocket,
    gemini_ws: websockets.WebSocketClientProtocol,
) -> None:
    try:
        while True:
            raw = await client_ws.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await _send_error(client_ws, "Invalid JSON payload from client.")
                continue

            msg_type = message.get("type")
            payload = message.get("payload") or {}

            if msg_type == "audio":
                audio = {
                    "realtimeInput": {
                        "audio": {
                            "data": payload.get("data", ""),
                            "mimeType": payload.get(
                                "mimeType", "audio/pcm;rate=16000"
                            ),
                        }
                    }
                }
                await gemini_ws.send(json.dumps(audio))
            elif msg_type == "text":
                text_message = {
                    "realtimeInput": {"text": payload.get("text", "")}
                }
                await gemini_ws.send(json.dumps(text_message))
            elif msg_type == "end":
                await gemini_ws.close()
                return
    except WebSocketDisconnect:
        return
    except websockets.ConnectionClosed as exc:
        await _send_error(
            client_ws,
            f"Gemini socket closed while sending audio: {exc.code} {exc.reason}",
        )
        return


async def _forward_gemini_to_client(
    client_ws: WebSocket,
    gemini_ws: websockets.WebSocketClientProtocol,
    session_id: str,
    buffers: LiveSessionBuffers,
) -> None:
    try:
        async for raw in gemini_ws:
            response = json.loads(raw)

            if response.get("error"):
                await client_ws.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "payload": {
                                "message": response.get("error").get("message", "")
                            },
                        }
                    )
                )
                continue

            server_content = response.get("serverContent") or {}
            input_transcription = server_content.get("inputTranscription")
            if input_transcription and input_transcription.get("text"):
                buffers.current_input = _merge_transcript(
                    buffers.current_input,
                    input_transcription.get("text", ""),
                )
                await client_ws.send_text(
                    json.dumps(
                        {
                            "type": "input_transcript",
                            "payload": {"text": input_transcription.get("text", "")},
                        }
                    )
                )

            output_transcription = server_content.get("outputTranscription")
            if output_transcription and output_transcription.get("text"):
                buffers.current_output = _merge_transcript(
                    buffers.current_output,
                    output_transcription.get("text", ""),
                )
                await client_ws.send_text(
                    json.dumps(
                        {
                            "type": "output_transcript",
                            "payload": {"text": output_transcription.get("text", "")},
                        }
                    )
                )

            if server_content.get("turnComplete"):
                user_final = buffers.current_input.strip()
                model_final = buffers.current_output.strip()
                is_duplicate = (
                    user_final == buffers.last_input
                    and model_final == buffers.last_output
                )

                if not is_duplicate:
                    buffers.last_input = user_final
                    buffers.last_output = model_final
                    if user_final:
                        append_session_turn(session_id, "user", user_final)
                    if model_final:
                        append_session_turn(session_id, "model", model_final)

                buffers.current_input = ""
                buffers.current_output = ""
                await client_ws.send_text(json.dumps({"type": "turn_complete"}))

            if server_content.get("interrupted"):
                buffers.current_input = ""
                buffers.current_output = ""
                await client_ws.send_text(json.dumps({"type": "interrupted"}))

            model_turn = server_content.get("modelTurn") or {}
            for part in model_turn.get("parts", []) or []:
                inline_data = part.get("inlineData") or {}
                if inline_data.get("data"):
                    await client_ws.send_text(
                        json.dumps(
                            {
                                "type": "audio",
                                "payload": {
                                    "data": inline_data.get("data"),
                                    "mimeType": inline_data.get(
                                        "mimeType", "audio/pcm;rate=24000"
                                    ),
                                },
                            }
                        )
                    )
    except websockets.ConnectionClosed as exc:
        await _send_error(
            client_ws,
            f"Gemini socket closed: {exc.code} {exc.reason}",
        )


@router.websocket("/live")
async def live_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("Client websocket accepted")

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        await _send_error(websocket, "Missing GEMINI_API_KEY on server.")
        await websocket.close(code=1011)
        return

    config_payload = await _receive_initial_config(websocket)
    if config_payload is None:
        logger.warning("Client closed before sending config")
        await websocket.close(code=1000)
        return

    session_id = config_payload.get("sessionId")
    session = get_session(session_id)
    if not session:
        await _send_error(websocket, "Session not found.")
        await websocket.close(code=1008)
        return

    ws_url = GEMINI_WS_URL.format(api_key=api_key)

    try:
        logger.info("Connecting to Gemini Live API")
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as gemini_ws:
            config_message = _build_gemini_config(config_payload, session.system_prompt)
            await gemini_ws.send(json.dumps(config_message))
            await websocket.send_text(json.dumps({"type": "ready"}))
            logger.info("Gemini config sent, session ready")

            buffers = LiveSessionBuffers()

            client_task = asyncio.create_task(
                _forward_client_to_gemini(websocket, gemini_ws)
            )
            gemini_task = asyncio.create_task(
                _forward_gemini_to_client(websocket, gemini_ws, session_id, buffers)
            )

            done, pending = await asyncio.wait(
                {client_task, gemini_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
    except Exception as exc:
        await _send_error(websocket, f"Backend Live API error: {exc}")
    finally:
        with suppress(Exception):
            await websocket.close()
        logger.info("Client websocket closed")
