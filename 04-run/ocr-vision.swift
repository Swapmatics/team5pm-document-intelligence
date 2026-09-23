import Foundation
import Vision
import AppKit

let args = CommandLine.arguments
if args.count < 2 {
    fputs("usage: ocr-vision image.png\n", stderr)
    exit(2)
}
let url = URL(fileURLWithPath: args[1])
guard let image = NSImage(contentsOf: url),
      let tiff = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiff),
      let cg = bitmap.cgImage else {
    fputs("could not read the page image\n", stderr)
    exit(1)
}
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
let handler = VNImageRequestHandler(cgImage: cg, options: [:])
do {
    try handler.perform([request])
} catch {
    fputs("ocr failed\n", stderr)
    exit(1)
}
let lines = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
print(lines.joined(separator: "\n"))
