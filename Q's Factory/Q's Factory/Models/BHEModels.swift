import Foundation

enum BHEEntryKind: String, Codable, Hashable, CaseIterable {
    case cpk
    case apt
    case lzs
    case texture
    case model
    case part
    case course
    case field
    case shop
    case text
    case unknown

    var displayName: String {
        switch self {
        case .cpk: "CPK"
        case .apt: "APT"
        case .lzs: "LZS"
        case .texture: "Texture"
        case .model: "Model"
        case .part: "Part"
        case .course: "Course"
        case .field: "Field"
        case .shop: "Shop"
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
        case .part: "wrench.adjustable"
        case .course: "road.lanes"
        case .field: "map"
        case .shop: "storefront"
        case .text: "text.alignleft"
        case .unknown: "questionmark.square"
        }
    }
}

enum BHESupportState: String, Codable, Hashable, CaseIterable {
    case supported
    case readOnly = "read-only"
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

enum BHEPreviewBackground: String, CaseIterable, Identifiable {
    case checkerboard
    case black
    case white

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .checkerboard: "Checkerboard"
        case .black: "Black"
        case .white: "White"
        }
    }
}

enum BHESourceKind: String, Codable, Hashable {
    case iso
    case discRoot
    case egameISO
    case egameDiscRoot

    var displayName: String {
        switch self {
        case .iso: "ISO"
        case .discRoot: "Mounted BHE Disc"
        case .egameISO: "Road Trip ISO"
        case .egameDiscRoot: "Mounted Road Trip Disc"
        }
    }

    var isEGame: Bool {
        switch self {
        case .egameISO, .egameDiscRoot:
            true
        case .iso, .discRoot:
            false
        }
    }
}

enum BHEWorkspaceAction {
    case extractSelected
    case extractContainer
    case validateReplacement
    case createPatchedCopy
    case revealLastOutput
    case verifyISO
    case exportOperationLog
    case showOriginalLocation

    var label: String {
        switch self {
        case .extractSelected: "Extract Selected Texture..."
        case .extractContainer: "Export All Textures in Container..."
        case .validateReplacement: "Validate Replacement..."
        case .createPatchedCopy: "Create Patched Copy..."
        case .revealLastOutput: "Reveal in Finder"
        case .verifyISO: "Verify ISO"
        case .exportOperationLog: "Export Operation Log..."
        case .showOriginalLocation: "Show Original Location"
        }
    }

    var systemImage: String {
        switch self {
        case .extractSelected: "square.and.arrow.down"
        case .extractContainer: "tray.and.arrow.down"
        case .validateReplacement: "checkmark.shield"
        case .createPatchedCopy: "doc.badge.plus"
        case .revealLastOutput: "finder"
        case .verifyISO: "checkmark.seal"
        case .exportOperationLog: "doc.text"
        case .showOriginalLocation: "location.viewfinder"
        }
    }
}

struct BHEUserFacingError: Identifiable, Hashable {
    let id = UUID()
    let title: String
    let explanation: String
    let suggestion: String?
    let technicalDetails: String?
    let relatedEntryID: String?
    let safeToRetry: Bool
    let originalISOModified: Bool
    let patchedCopyWritten: Bool

    var statusSummary: String {
        if originalISOModified {
            return "\(title) Original ISO may have changed."
        }
        if patchedCopyWritten {
            return "\(title) A patched copy was written."
        }
        return "\(title) Original ISO was not modified."
    }
}

struct BHEISOSummary: Identifiable, Codable, Hashable {
    let id: String
    let isoName: String
    let gameTitle: String
    let variant: String
    let sourceFamily: String?
    let cpkCount: Int
    let textureCount: Int
}

struct BHEContainer: Identifiable, Codable, Hashable {
    let id: String
    let name: String
    let entryCount: Int
    let textureCount: Int
    let sector: Int
    let support: BHESupportState
}

struct BHEScanResult: Codable, Hashable {
    let iso: BHEISOSummary
    let containers: [BHEContainer]
    let entries: [BHEEntry]
}

struct BHETexturePreviewResult: Codable, Hashable {
    let entryID: String
    let pngPath: String
    let width: Int
    let height: Int
    let hasAlpha: Bool
    let originalISOModified: Bool
    let patchedCopyWritten: Bool
}

struct BHETextureExtractionResult: Codable, Hashable {
    let entryID: String
    let pngPath: String
    let width: Int
    let height: Int
    let hasAlpha: Bool
    let overwroteExisting: Bool
    let originalISOModified: Bool
    let patchedCopyWritten: Bool
}

struct BHEEntry: Identifiable, Codable, Hashable {
    let id: String
    let containerID: String
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
    let compression: String

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
        if offsetBytes < 0 {
            return "-"
        }
        return "0x" + String(offsetBytes, radix: 16, uppercase: true)
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
