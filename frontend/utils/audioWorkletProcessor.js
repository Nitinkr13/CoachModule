class PcmCaptureProcessor extends AudioWorkletProcessor {
  process(inputs, outputs) {
    const input = inputs[0];
    if (input && input[0]) {
      const channelData = input[0];
      const copy = new Float32Array(channelData.length);
      copy.set(channelData);
      this.port.postMessage(copy, [copy.buffer]);
    }

    const output = outputs[0];
    if (output) {
      for (const channel of output) {
        channel.fill(0);
      }
    }

    return true;
  }
}

registerProcessor('pcm-capture', PcmCaptureProcessor);
