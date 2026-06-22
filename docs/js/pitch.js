// Phase 2 (NOT wired up yet): microphone note-checking.
//
// Plan: getUserMedia -> AnalyserNode (fftSize 2048) -> requestAnimationFrame loop
// -> pitchy McLeod pitch detection. Compare the detected MIDI note to the expected
// note at the cursor (piece JSON event), with a clarity threshold and octave
// tolerance. See the project plan for details.
//
// Sketch (to be fleshed out and imported by main.js when Phase 2 begins):
//
//   import { PitchDetector } from "https://cdn.jsdelivr.net/npm/pitchy@4/+esm";
//
//   export async function startMic(onPitch) {
//     const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
//     const ctx = new AudioContext();
//     const src = ctx.createMediaStreamSource(stream);
//     const analyser = ctx.createAnalyser();
//     analyser.fftSize = 2048;
//     src.connect(analyser);
//     const detector = PitchDetector.forFloat32Array(analyser.fftSize);
//     detector.minVolumeDecibels = -35;
//     const buf = new Float32Array(detector.inputLength);
//     (function loop() {
//       analyser.getFloatTimeDomainData(buf);
//       const [hz, clarity] = detector.findPitch(buf, ctx.sampleRate);
//       if (clarity >= 0.9 && hz > 0) {
//         const midi = Math.round(69 + 12 * Math.log2(hz / 440));
//         onPitch(midi);
//       }
//       requestAnimationFrame(loop);
//     })();
//   }

export const PHASE_2_PLACEHOLDER = true;
