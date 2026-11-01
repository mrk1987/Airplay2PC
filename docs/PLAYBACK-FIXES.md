# Playback repairs

- Strip PyAV alignment padding before audio output. A 352-sample stereo s16 frame
  has 1,408 valid bytes, but its resampled plane allocates 1,536 bytes. Playing
  all 1,536 adds 32 unwanted samples per channel every packet: 9.09% excess time
  plus arbitrary padding noise. Earlier buffered logs also show 4,224 bytes where
  4,096 are valid. This is a measured bug, not a codec-bit-depth guess.
- Preserve every decoded/resampled frame, including zero or multiple resampler outputs.
- Stop reading `48000` as `8000` when parsing the negotiated format.
- Keep packet, sequence and timestamp queues consistent when removing a packet.
  Sequence zero now works at rollover; flush preserves order and handles empty queues.
- Skip stale resends and choose the nearest future sequence after a gap.
- Configure 24-bit decode with PyAV's s32 container, match mono/stereo output,
  and use the negotiated ALAC samples per frame.
- Correct the legacy AES-key/IV selection condition.
- Route iPhone volume commands to the Windows playback process rather than the
  network-control process; the latter owns no audio session. Andreas confirmed the slider now controls PC volume.
- Remove unconditional plaintext and WAV recording from playback. Existing recordings stay local.

Seven regression tests pass, including nonzero stereo ALAC roundtrips for 16/24-bit
and 352/1024 samples, exact output size/channel order, rate selection across all
enumerated formats, sequence rollover, out-of-order packets, and empty flush.
Native startup and mDNS registration succeeded; Andreas confirmed clean sound.
This does not prove every fix contributed to that improvement.
