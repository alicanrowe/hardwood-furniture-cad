// vtenc IN_DIR OUT.mp4 : encode o#####.jpg (sorted) at 12 fps source -> 24 fps H.264 High, 40 Mbps, GOP 48, faststart
import Foundation
import AVFoundation
import CoreImage
import ImageIO
let a = CommandLine.arguments
let inDir = a[1], outPath = a[2]
let files = try FileManager.default.contentsOfDirectory(atPath: inDir).filter { $0.hasSuffix(".jpg") && $0.hasPrefix("o") }.sorted()
guard let first = files.first,
      let s0 = CGImageSourceCreateWithURL(URL(fileURLWithPath: inDir + "/" + first) as CFURL, nil),
      let im0 = CGImageSourceCreateImageAtIndex(s0, 0, nil) else { fatalError("no frames") }
let W = im0.width, H = im0.height
let outURL = URL(fileURLWithPath: outPath)
let w = try AVAssetWriter(outputURL: outURL, fileType: .mp4)
w.shouldOptimizeForNetworkUse = true
let settings: [String: Any] = [
  AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: W, AVVideoHeightKey: H,
  AVVideoCompressionPropertiesKey: [
    AVVideoAverageBitRateKey: 40_000_000, AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
    AVVideoMaxKeyFrameIntervalKey: 48, AVVideoExpectedSourceFrameRateKey: 24, AVVideoAllowFrameReorderingKey: true,
    AVVideoH264EntropyModeKey: AVVideoH264EntropyModeCABAC]]
let inp = AVAssetWriterInput(mediaType: .video, outputSettings: settings)
inp.expectsMediaDataInRealTime = false
let ad = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: inp, sourcePixelBufferAttributes: [
  kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA, kCVPixelBufferWidthKey as String: W, kCVPixelBufferHeightKey as String: H])
w.add(inp); w.startWriting(); w.startSession(atSourceTime: .zero)
var t: Int64 = 0
for (i, f) in files.enumerated() {
  autoreleasepool {
    guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: inDir + "/" + f) as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else { fatalError("bad frame \(f)") }
    var pb: CVPixelBuffer?
    CVPixelBufferPoolCreatePixelBuffer(nil, ad.pixelBufferPool!, &pb)
    let b = pb!
    CVPixelBufferLockBaseAddress(b, [])
    let ctx = CGContext(data: CVPixelBufferGetBaseAddress(b), width: W, height: H, bitsPerComponent: 8,
      bytesPerRow: CVPixelBufferGetBytesPerRow(b), space: CGColorSpace(name: CGColorSpace.sRGB)!,
      bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue)!
    ctx.draw(img, in: CGRect(x: 0, y: 0, width: W, height: H))
    CVPixelBufferUnlockBaseAddress(b, [])
    for _ in 0..<2 {   // hold each 12 fps frame for 2 output frames at 24 fps
      while !inp.isReadyForMoreMediaData { usleep(2000) }
      if !ad.append(b, withPresentationTime: CMTime(value: t, timescale: 24)) { fatalError("append failed \(w.error!)") }
      t += 1
    }
  }
  if i % 200 == 0 { print("frame", i, "/", files.count); fflush(stdout) }
}
inp.markAsFinished()
let sem = DispatchSemaphore(value: 0)
w.finishWriting { sem.signal() }
sem.wait()
if w.status != .completed { fatalError("writer failed: \(String(describing: w.error))") }
print("wrote", outPath, W, "x", H, "frames", t)
