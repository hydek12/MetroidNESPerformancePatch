import CryptoKit
import Foundation

let arguments = CommandLine.arguments.dropFirst()
if arguments.count == 1, arguments.first == "--help" {
    print("Usage: metroid-rom-info <rom-file>")
    exit(EXIT_SUCCESS)
}

guard arguments.count == 1, let path = arguments.first else {
    FileHandle.standardError.write(Data("Usage: metroid-rom-info <rom-file>\n".utf8))
    exit(EXIT_FAILURE)
}

do {
    let data = try Data(contentsOf: URL(fileURLWithPath: path))
    let digest = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    print("\(digest)  \(path)")
} catch {
    FileHandle.standardError.write(Data("Could not read \(path): \(error.localizedDescription)\n".utf8))
    exit(EXIT_FAILURE)
}
