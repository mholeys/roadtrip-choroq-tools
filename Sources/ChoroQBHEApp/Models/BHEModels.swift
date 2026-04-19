import Foundation

enum BHEEntryKind: String, Codable, Hashable, CaseIterable {
    case cpk
    case apt
    case lzs
    case texture
    case model
    case text
    case unknown

    var displayName: String {
        switch self {
        case .cpk: "CPK"
        case .apt: "APT"
        case .lzs: "LZS"
        case .texture: "Texture"
        case .model: "Model"
        case .text: "Text"
        case .unknown: "Unknown"
        }
    }

    var systemImage: String {
        switch self {
        case .cpk: "shippingbox"
        case .apt: "square.grid.3x3"
        case .lzs: "archivebox"
        case .texture: "photo"
        case .model: "cube"
        case .text: "text.alignleft"
        case .unknown: "questionmark.square"
        }
    }
}

enum BHESupportState: String, Codable, Hashable, CaseIterable {
    case supported
    case readOnly
    case compressed
    case risky
    case unknown

    var displayName: String {
        switch self {
        case .supported: "Supported"
        case .readOnly: "Read-only"
        case .compressed: "Compressed"
        case .risky: "Risky"
        case .unknown: "Unknown"
        }
    }

    var systemImage: String {
        switch self {
        case .supported: "checkmark.circle"
        case .readOnly: "eye"
        case .compressed: "archivebox"
        case .risky: "exclamationmark.triangle"
        case .unknown: "questionmark.circle"
        }
    }
}

struct BHEISOSummary: Identifiable, Codable, Hashable {
    let id: String
    let isoName: String
    let gameTitle: String
    let variant: String
    let cpkCount: Int
    let textureCount: Int
}

struct BHEScanResult: Codable, Hashable {
    let iso: BHEISOSummary
    let entries: [BHEEntry]
}

struct BHEEntry: Identifiable, Codable, Hashable {
    let id: String
    let cpkName: String
    let name: String
    let kind: BHEEntryKind
    let format: String
    let width: Int?
    let height: Int?
    let paletteSize: Int?
    let sizeBytes: Int
    let offsetBytes: Int
    let sector: Int
    let support: BHESupportState
    let canExtract: Bool
    let canReplace: Bool

    var dimensionsText: String {
        guard let width, let height else {
            return "-"
        }
        return "\(width)x\(height)"
    }

    var paletteText: String {
        guard let paletteSize else {
            return "-"
        }
        return "\(paletteSize)"
    }

    var offsetText: String {
        "0x" + String(offsetBytes, radix: 16, uppercase: true)
    }

    var sizeText: String {
        ByteCountFormatter.string(fromByteCount: Int64(sizeBytes), countStyle: .file)
    }
}

struct BHEEntryGroup: Identifiable, Hashable {
    let id: String
    let title: String
    let detail: String
    let systemImage: String
}
