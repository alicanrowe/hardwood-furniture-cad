// vcheck VIDEO OUTDIR PREFIX srcFrame:name ... : count frames, duration, size; extract stills at source frames (12fps src held x2 at 24fps)
import Foundation
import AVFoundation
import ImageIO
import UniformTypeIdentifiers
let a = CommandLine.arguments
let url = URL(fileURLWithPath: a[1]), outDir = a[2], prefix = a[3]
let asset = AVURLAsset(url: url, options: [AVURLAssetPreferPreciseDurationAndTimingKey: true])
let sem = DispatchSemaphore(value: 0)
var track: AVAssetTrack!; var dur = CMTime.zero; var size = CGSize.zero; var fps: Float = 0
Task {
  track = try! await asset.loadTracks(withMediaType: .video).first!
  dur = try! await asset.load(.duration)
  size = try! await track.load(.naturalSize); fps = try! await track.load(.nominalFrameRate)
  sem.signal() }
sem.wait()
let r = try! AVAssetReader(asset: asset)
let o = AVAssetReaderTrackOutput(track: track, outputSettings: nil); o.alwaysCopiesSampleData = false
r.add(o); r.startReading()
var n = 0
while let s = o.copyNextSampleBuffer() { n += CMSampleBufferGetNumSamples(s) }
print("frames", n, "duration_s", String(format: "%.3f", dur.seconds), "size", Int(size.width), "x", Int(size.height), "fps", fps)
let g = AVAssetImageGenerator(asset: asset)
g.requestedTimeToleranceBefore = .zero; g.requestedTimeToleranceAfter = .zero; g.appliesPreferredTrackTransform = true
for spec in a.dropFirst(4) {
  let p = spec.split(separator: ":"); let f = Int(p[0])!; let name = String(p[1])
  let k = (f - 1) / 2
  let t = CMTime(value: Int64(2 * k), timescale: 24)
  let img = try! g.copyCGImage(at: t, actualTime: nil)
  let out = URL(fileURLWithPath: "\(outDir)/\(prefix)_\(name)_f\(String(format: "%04d", f)).png")
  let d = CGImageDestinationCreateWithURL(out as CFURL, UTType.png.identifier as CFString, 1, nil)!
  CGImageDestinationAddImage(d, img, nil); CGImageDestinationFinalize(d)
  print("still", out.lastPathComponent)
}
