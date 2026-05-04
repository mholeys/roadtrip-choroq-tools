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
    case graphics
    case sound
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
        case .graphics: "Graphics"
        case .sound: "Sound"
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
        case .graphics: "rectangle.stack"
        case .sound: "waveform"
        case .text: "text.alignleft"
        case .unknown: "questionmark.square"
        }
    }
}

enum BHESupportState: String, Codable, Hashable, CaseIterable {
    case supported
    case exportable
    case scanOnly = "scan-only"
    case unsupported
    case readOnly = "read-only"
    case compressed
    case risky
    case unknown

    var displayName: String {
        switch self {
        case .supported: "Supported"
        case .exportable: "Exportable"
        case .scanOnly: "Scan only"
        case .unsupported: "Unsupported"
        case .readOnly: "Read-only"
        case .compressed: "Compressed"
        case .risky: "Risky"
        case .unknown: "Unknown"
        }
    }

    var systemImage: String {
        switch self {
        case .supported: "checkmark.circle"
        case .exportable: "square.and.arrow.down"
        case .scanOnly: "doc.text.magnifyingglass"
        case .unsupported: "nosign"
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
    case generatePreview
    case openTheatre
    case quickLookPreview
    case export3DAsset
    case exportShopTextures
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
        case .generatePreview: "Generate Preview"
        case .openTheatre: "Open in Theatre View"
        case .quickLookPreview: "Quick Look Preview"
        case .export3DAsset: "Export 3D Asset..."
        case .exportShopTextures: "Export Shop Textures..."
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
        case .generatePreview: "wand.and.stars"
        case .openTheatre: "rectangle.inset.filled"
        case .quickLookPreview: "eye"
        case .export3DAsset: "cube.transparent"
        case .exportShopTextures: "photo.stack"
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

enum BHEOperationLogLevel: String, Codable, Hashable {
    case info
    case warning
    case error
}

struct BHEOperationLogEntry: Identifiable, Codable, Hashable {
    let id: UUID
    let date: Date
    let level: BHEOperationLogLevel
    let title: String
    let details: String?
    let sourcePath: String?
    let entryID: String?
    let sourceModified: Bool
    let patchedCopyWritten: Bool

    init(
        id: UUID = UUID(),
        date: Date = Date(),
        level: BHEOperationLogLevel,
        title: String,
        details: String? = nil,
        sourcePath: String? = nil,
        entryID: String? = nil,
        sourceModified: Bool = false,
        patchedCopyWritten: Bool = false
    ) {
        self.id = id
        self.date = date
        self.level = level
        self.title = title
        self.details = details
        self.sourcePath = sourcePath
        self.entryID = entryID
        self.sourceModified = sourceModified
        self.patchedCopyWritten = patchedCopyWritten
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
    let displayName: String?
    let entryCount: Int
    let textureCount: Int
    let sector: Int
    let support: BHESupportState

    var displayTitle: String {
        displayName ?? name
    }
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

struct BHEExportManifest: Codable, Hashable {
    let operationID: String
    let sourceModified: Bool
    let patchedCopyWritten: Bool
    let entryIDs: [String]
    let outputRoot: String
    let primaryPreviewPath: String?
    let files: [BHEExportedFile]
    let overwrittenFiles: [String]
    let warnings: [String]

    var previewImageURL: URL? {
        files.first { file in
            file.previewable && file.kind == "texture" && file.path.lowercased().hasSuffix(".png")
        }.map { URL(fileURLWithPath: $0.path) }
    }

    var previewModelURL: URL? {
        files.first { file in
            file.previewable && file.kind == "model" && file.path.lowercased().hasSuffix(".obj")
        }.map { URL(fileURLWithPath: $0.path) }
    }

    var primaryPreviewURL: URL? {
        primaryPreviewPath.map { URL(fileURLWithPath: $0) }
    }
}

enum AssetPreviewKind: String, Codable, Hashable, CaseIterable {
    case none
    case metadataOnly
    case rasterImage
    case modelScene
    case audio
    case audioCandidate
    case quickLookFile
    case unsupported

    var displayName: String {
        switch self {
        case .none: "No Preview"
        case .metadataOnly: "Metadata"
        case .rasterImage: "Image"
        case .modelScene: "Scene"
        case .audio: "Audio"
        case .audioCandidate: "Audio Candidate"
        case .quickLookFile: "Quick Look"
        case .unsupported: "Unsupported"
        }
    }

    var systemImage: String {
        switch self {
        case .none: "minus.circle"
        case .metadataOnly: "doc.text.magnifyingglass"
        case .rasterImage: "photo"
        case .modelScene: "cube.transparent"
        case .audio: "waveform"
        case .audioCandidate: "waveform.badge.magnifyingglass"
        case .quickLookFile: "eye"
        case .unsupported: "nosign"
        }
    }
}

enum AssetPreviewState: Hashable {
    case idle
    case preparing(stage: String)
    case ready
    case partial(reason: String)
    case failed(message: String)
    case unsupported(reason: String)

    var title: String {
        switch self {
        case .idle: "Select a Part"
        case .preparing: "Preparing Preview"
        case .ready: "Preview Ready"
        case .partial: "Partial Preview"
        case .failed: "Decoder Failed"
        case .unsupported: "Unsupported"
        }
    }

    var message: String? {
        switch self {
        case .idle:
            nil
        case .preparing(let stage):
            stage
        case .ready:
            nil
        case .partial(let reason), .failed(let reason), .unsupported(let reason):
            reason
        }
    }

    var systemImage: String {
        switch self {
        case .idle: "circle"
        case .preparing: "clock"
        case .ready: "checkmark.circle"
        case .partial: "circle.lefthalf.filled"
        case .failed: "xmark.octagon"
        case .unsupported: "nosign"
        }
    }
}

enum PlaybackState: Hashable {
    case stopped
    case loading
    case playing
    case paused
    case failed(message: String)

    var isActive: Bool {
        switch self {
        case .stopped, .failed:
            false
        case .loading, .playing, .paused:
            true
        }
    }
}

struct MaterialRelinkReport: Codable, Hashable {
    var automaticTextureCount: Int
    var manuallyRelinkedMaterialNames: [String]
    var unresolvedMaterialNames: [String]
    var warnings: [String]

    static let empty = MaterialRelinkReport(
        automaticTextureCount: 0,
        manuallyRelinkedMaterialNames: [],
        unresolvedMaterialNames: [],
        warnings: []
    )

    var summary: String {
        if !unresolvedMaterialNames.isEmpty {
            return "Manual material relink applied with \(unresolvedMaterialNames.count) unresolved material(s)."
        }
        if !manuallyRelinkedMaterialNames.isEmpty {
            return "Manual material relink applied to \(manuallyRelinkedMaterialNames.count) material(s)."
        }
        if automaticTextureCount > 0 {
            return "SceneKit resolved \(automaticTextureCount) texture reference(s)."
        }
        return "No material textures were resolved."
    }
}

struct DecoderDiagnostic: Identifiable, Codable, Hashable {
    let id: UUID
    let title: String
    let detail: String

    init(id: UUID = UUID(), title: String, detail: String) {
        self.id = id
        self.title = title
        self.detail = detail
    }
}

struct AssetAudioItem: Identifiable, Hashable {
    let id: String
    let entryID: String
    let title: String
    let sourceFormat: String
    let playableURL: URL?
    let duration: TimeInterval?
    let sampleRate: Double?
    let channels: Int?
}

struct TheatrePreviewItem: Identifiable, Hashable {
    let id: String
    let entryID: String
    let title: String
    let kind: AssetPreviewKind
    let url: URL?
    let manifest: BHEExportManifest?
}

struct VerboseConsoleOperation: Identifiable, Hashable {
    let id: String
    let title: String
    let entryID: String?
    let manifest: BHEExportManifest?
    let diagnostics: [DecoderDiagnostic]
    let relinkReport: MaterialRelinkReport?
    let logEntries: [BHEOperationLogEntry]
}

struct BHEExportedFile: Codable, Hashable {
    let path: String
    let kind: String
    let role: String
    let previewable: Bool
    let mediaType: String?
    let applied: Bool?
    let sizeBytes: Int?
    let warning: String?

    var fileName: String {
        URL(fileURLWithPath: path).lastPathComponent
    }

    var pathExtension: String {
        URL(fileURLWithPath: path).pathExtension.uppercased()
    }

    var exists: Bool {
        FileManager.default.fileExists(atPath: path)
    }
}

struct BHEExpectedExportOutput: Codable, Hashable {
    let kind: String
    let `extension`: String
    let role: String
    let previewable: Bool
}

struct BHESectionNames: Codable, Hashable {
    let index: Int?
    let names: [String]
}

struct BHEEntry: Identifiable, Codable, Hashable {
    let id: String
    let containerID: String
    let cpkName: String
    let serviceBayName: String?
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
    let meshCount: Int?
    let textureCount: Int?
    let descriptor: String?
    let modelDescription: String?
    let expectedExportOutputs: [BHEExpectedExportOutput]?
    let supportReason: String?
    let unsupportedReason: String?
    let sectionNames: [BHESectionNames]?
    let partSectionNames: [String]?
    let supportedOperations: [String]?

    var serviceBayDisplayName: String {
        serviceBayName ?? cpkName
    }

    var isExportableEGameModel: Bool {
        id.hasPrefix("egame:")
            && kind == .model
            && canExtract
            && support == .exportable
            && supportedOperations?.contains("extract-egame-car") == true
    }

    var isExportableEGameShopTextures: Bool {
        id.hasPrefix("egame:")
            && kind == .shop
            && canExtract
            && support == .exportable
            && supportedOperations?.contains("extract-egame-shop-textures") == true
    }

    var exportRoleSummary: String? {
        guard let expectedExportOutputs, !expectedExportOutputs.isEmpty else {
            return nil
        }
        let roles = expectedExportOutputs.map(\.role)
        return roles.joined(separator: ", ")
    }

    var sectionCountHint: Int? {
        sectionNames?.count
    }

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

struct BHEMissingGUIReport: Codable, Hashable {
    let sourcePath: String
    let discoveredFileCount: Int
    let representedEntryCount: Int
    let missingFileCount: Int
    let groups: [BHEMissingGUIAssetGroup]
    let assets: [BHEMissingGUIAsset]
}

struct BHEMissingGUIAssetGroup: Codable, Hashable, Identifiable {
    let role: String
    let count: Int
    let assets: [BHEMissingGUIAsset]

    var id: String { role }
}

struct BHEMissingGUIAsset: Codable, Hashable, Identifiable {
    let path: String
    let `extension`: String
    let sizeBytes: Int
    let guessedRole: String
    let pythonUnderstands: Bool
    let availableOperations: [String]
    let capability: String
    let missingReason: String

    var id: String { path }

    var sizeText: String {
        ByteCountFormatter.string(fromByteCount: Int64(sizeBytes), countStyle: .file)
    }
}
