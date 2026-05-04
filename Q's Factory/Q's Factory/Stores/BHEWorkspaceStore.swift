import Foundation
import AppKit
import Observation
import UniformTypeIdentifiers

@MainActor
@Observable
final class BHEWorkspaceStore {
    private let backend: BHEBackendClient

    var isoURL: URL?
    var sourceKind: BHESourceKind?
    var isoSummary: BHEISOSummary?
    var containers: [BHEContainer] = []
    var entries: [BHEEntry] = []
    var selectedGroupID = "all"
    var selectedEntryID: BHEEntry.ID?
    var searchText = ""
    var showUnsupportedEntries = true
    var showCompressedEntries = true
    var isInspectorPresented = true
    var previewBackground: BHEPreviewBackground = .checkerboard
    var isLoading = false
    var isBackendDiagnosticsPresented = false
    var isBackendDiagnosticsLoading = false
    var backendVersion: BHEBackendVersion?
    var backendHealth: BHEBackendHealth?
    var supportedTypes: BHESupportedTypes?
    var availableBackendCommands: Set<String> = []
    var statusMessage = "Open a PlayStation 2 ISO, BIN/CUE pair, or mounted source folder to start."
    var userError: BHEUserFacingError?
    var lastOutputURL: URL?
    var previewEntryID: BHEEntry.ID?
    var previewImageURL: URL?
    var previewModelURL: URL?
    var previewManifest: BHEExportManifest?
    var selectedPreviewManifest: BHEExportManifest?
    var previewKind: AssetPreviewKind = .none
    var previewState: AssetPreviewState = .idle
    var previewStageText = ""
    var generatedFiles: [BHEExportedFile] = []
    var quickLookURL: URL?
    var theatrePreviewItem: TheatrePreviewItem?
    var activeAudioItem: AssetAudioItem?
    var playbackState: PlaybackState = .stopped
    @ObservationIgnored var previewTask: Task<Void, Never>?
    var currentOperationID: String?
    var materialRelinkReport: MaterialRelinkReport = .empty
    var decoderDiagnostics: [DecoderDiagnostic] = []
    var verboseConsoleOperation: VerboseConsoleOperation?
    var missingGUIReport: BHEMissingGUIReport?
    var isPreviewLoading = false
    var previewFailureMessage: String?
    var operationLog: [BHEOperationLogEntry] = []
    var sourceKindDisplayName: String {
        sourceKind?.displayName ?? "No Source"
    }

    init(backend: BHEBackendClient) {
        self.backend = backend
    }

    var hasWorkspace: Bool {
        isoSummary != nil
    }

    var groups: [BHEEntryGroup] {
        let cpkGroups = containers.map { container in
            BHEEntryGroup(
                id: container.id,
                title: container.displayTitle,
                detail: container.textureCount > 0
                    ? "\(container.entryCount) parts, \(container.textureCount) textures"
                    : "\(container.entryCount) parts",
                systemImage: containerSystemImage(for: container)
            )
        }

        return [
            BHEEntryGroup(
                id: "all",
                title: "All Parts",
                detail: "\(entries.count) parts",
                systemImage: "wrench.and.screwdriver"
            )
        ] + roleGroups + cpkGroups + diagnosticGroups
    }

    var filteredEntries: [BHEEntry] {
        let groupEntries: [BHEEntry]
        if selectedGroupID == "all" {
            groupEntries = entries
        } else if let role = roleKind(for: selectedGroupID) {
            groupEntries = entries.filter { $0.kind == role }
        } else if selectedGroupID == "diagnostics.missing-gui" {
            groupEntries = entries.filter { $0.support == .unsupported || $0.support == .unknown }
        } else {
            groupEntries = entries.filter { $0.containerID == selectedGroupID }
        }

        let supportFiltered = groupEntries.filter { entry in
            if !showCompressedEntries && entry.support == .compressed {
                return false
            }
            if !showUnsupportedEntries && (entry.support == .unknown || entry.support == .unsupported) {
                return false
            }
            return true
        }

        let trimmedSearch = searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedSearch.isEmpty else {
            return supportFiltered
        }

        return supportFiltered.filter { entry in
            entry.name.localizedStandardContains(trimmedSearch)
            || entry.cpkName.localizedStandardContains(trimmedSearch)
            || entry.kind.displayName.localizedStandardContains(trimmedSearch)
            || entry.format.localizedStandardContains(trimmedSearch)
            || entry.id.localizedStandardContains(trimmedSearch)
        }
    }

    var selectedEntry: BHEEntry? {
        guard let selectedEntryID else {
            return nil
        }
        return entries.first { $0.id == selectedEntryID }
    }

    private var roleGroups: [BHEEntryGroup] {
        let definitions: [(String, String, BHEEntryKind, String)] = [
            ("role.cars", "Cars", .model, "car.side"),
            ("role.parts", "Car Parts", .part, "wrench.adjustable"),
            ("role.courses", "Race / Activity Courses", .course, "road.lanes"),
            ("role.fields", "World Fields", .field, "map"),
            ("role.shops", "Towns / Shops", .shop, "storefront"),
            ("role.textures", "Textures", .texture, "photo"),
            ("role.graphics", "Graphics", .graphics, "rectangle.stack"),
            ("role.sounds", "Sounds", .sound, "waveform"),
            ("role.unknown", "Unknown", .unknown, "questionmark.square")
        ]
        return definitions.compactMap { id, title, kind, image in
            let count = entries.filter { $0.kind == kind }.count
            guard count > 0 else { return nil }
            return BHEEntryGroup(id: id, title: title, detail: "\(count) file\(count == 1 ? "" : "s")", systemImage: image)
        }
    }

    private var diagnosticGroups: [BHEEntryGroup] {
        guard sourceKind?.isEGame == true else { return [] }
        let missingCount = missingGUIReport?.missingFileCount ?? 0
        let unsupportedCount = entries.filter { $0.support == .unsupported || $0.support == .unknown }.count
        return [
            BHEEntryGroup(
                id: "diagnostics.missing-gui",
                title: "Missing from GUI / Diagnostics",
                detail: missingCount > 0 ? "\(missingCount) missing" : "\(unsupportedCount) unknown or unsupported",
                systemImage: "exclamationmark.magnifyingglass"
            )
        ]
    }

    private func roleKind(for groupID: String) -> BHEEntryKind? {
        switch groupID {
        case "role.cars": return .model
        case "role.parts": return .part
        case "role.courses": return .course
        case "role.fields": return .field
        case "role.shops": return .shop
        case "role.textures": return .texture
        case "role.graphics": return .graphics
        case "role.sounds": return .sound
        case "role.unknown": return .unknown
        default: return nil
        }
    }

    var canExportSelectedEGameCar: Bool {
        guard let selectedEntry else {
            return false
        }
        return availableBackendCommands.contains("extract-egame-car")
            && canExportEGameCar(selectedEntry)
    }

    var canExportSelectedEGameShopTextures: Bool {
        guard let selectedEntry else {
            return false
        }
        return availableBackendCommands.contains("extract-egame-shop-textures")
            && canExportEGameShopTextures(selectedEntry)
    }

    var unsupportedEGameCarExportReason: String {
        guard let selectedEntry else {
            return "Select a Road Trip / HG2 / HG3 car body row to export it."
        }
        guard sourceKind?.isEGame == true else {
            return "3D asset export is available for Road Trip / HG2 / HG3 car model rows."
        }
        guard availableBackendCommands.contains("extract-egame-car") else {
            return "The bundled backend does not expose extract-egame-car yet. Run backend diagnostics after rebuilding."
        }
        guard selectedEntry.isExportableEGameModel else {
            return selectedEntry.unsupportedReason
                ?? "Only supported Road Trip / HG2 / HG3 car body rows can be exported in this phase."
        }
        return "Export is unavailable for this entry."
    }

    var unsupportedEGameShopTextureExportReason: String {
        guard let selectedEntry else {
            return "Select a Road Trip / HG2 shop row to export its textures."
        }
        guard sourceKind?.isEGame == true else {
            return "Shop texture export is available for Road Trip / HG2 shop rows."
        }
        guard availableBackendCommands.contains("extract-egame-shop-textures") else {
            return "The bundled backend does not expose extract-egame-shop-textures yet. Run backend diagnostics after rebuilding."
        }
        guard selectedEntry.isExportableEGameShopTextures else {
            return selectedEntry.unsupportedReason
                ?? "Only supported Road Trip / HG2 shop rows can export PNG textures in this phase."
        }
        return "Export is unavailable for this entry."
    }

    func openSourceWithPanel() async {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [
            UTType(filenameExtension: "iso"),
            UTType(filenameExtension: "bin"),
            UTType(filenameExtension: "cue"),
            .folder,
        ].compactMap { $0 }
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = true
        panel.canChooseFiles = true
        panel.message = "Choose an ISO now, or choose a BIN/CUE file or mounted folder for conversion guidance."
        panel.prompt = "Open Source"
        panel.nameFieldLabel = "Source:"

        guard panel.runModal() == .OK, let url = panel.url else {
            return
        }

        await openSource(at: url)
    }

    func openISOWithPanel() async {
        await openSourceWithPanel()
    }

    func openSource(at url: URL) async {
        let resourceValues = try? url.resourceValues(forKeys: [.isDirectoryKey])
        if resourceValues?.isDirectory == true {
            await openDiscRoot(at: url)
            return
        }

        switch url.pathExtension.lowercased() {
        case "iso":
            await openISO(at: url)
        case "bin", "cue":
            presentBINCUEGuidance(for: url)
        default:
            presentUnsupportedSourceError(
                title: "Unsupported Source Type",
                explanation: "The selected source is not a supported ISO, BIN, CUE, or mounted folder.",
                suggestion: "Choose a PlayStation 2 ISO for current scanning, or convert BIN/CUE pairs with bchunk first.",
                technicalDetails: "Path: \(url.path)"
            )
        }
    }

    func openISO(at url: URL) async {
        let didLoad = await performLoad {
            try await backend.scanISO(at: url)
        }
        if didLoad {
            isoURL = url
            sourceKind = isoSummary?.sourceFamily == "egame" ? .egameISO : .iso
            await refreshMissingGUIReportIfNeeded()
        }
    }

    func openDiscRoot(at url: URL) async {
        let shouldUseEGameScanner = looksLikeEGameDiscRoot(url)
        let didLoad = await performLoad {
            if shouldUseEGameScanner {
                try await backend.scanEGameDiscRoot(at: url)
            } else {
                try await backend.scanDiscRoot(at: url)
            }
        }
        if didLoad {
            isoURL = url
            sourceKind = isoSummary?.sourceFamily == "egame" ? .egameDiscRoot : .discRoot
            await refreshMissingGUIReportIfNeeded()
        }
    }

    func openEGameDiscRoot(at url: URL) async {
        let didLoad = await performLoad {
            try await backend.scanEGameDiscRoot(at: url)
        }
        if didLoad {
            isoURL = url
            sourceKind = .egameDiscRoot
            await refreshMissingGUIReportIfNeeded()
        }
    }

    func closeISO() {
        let closedPath = isoURL?.path
        isoURL = nil
        sourceKind = nil
        isoSummary = nil
        containers = []
        entries = []
        selectedGroupID = "all"
        selectedEntryID = nil
        searchText = ""
        missingGUIReport = nil
        clearPreview()
        statusMessage = "Closed source. Open another ISO, BIN/CUE pair, or mounted source folder to start."
        recordOperation(level: .info, title: "Closed source", details: closedPath)
    }

    func performAction(_ action: BHEWorkspaceAction) {
        switch action {
        case .extractSelected:
            Task { await extractSelectedTexture() }
        case .generatePreview:
            guard let selectedEntry else {
                presentNeedsSelectionError()
                return
            }
            previewTask?.cancel()
            previewTask = Task { await loadPreview(for: selectedEntry) }
        case .openTheatre:
            openTheatreForCurrentPreview()
        case .quickLookPreview:
            quickLookCurrentPreview()
        case .export3DAsset:
            Task { await extractSelectedEGameCar() }
        case .exportShopTextures:
            Task { await extractSelectedEGameShopTextures() }
        case .revealLastOutput:
            revealLastOutput()
        case .showOriginalLocation:
            guard let selectedEntry else {
                presentNeedsSelectionError()
                return
            }
            copyToPasteboard(selectedEntry.offsetText)
            statusMessage = "Copied original location offset for \(selectedEntry.name)."
        case .exportOperationLog:
            exportOperationLog()
        case .extractContainer, .validateReplacement, .createPatchedCopy, .verifyISO:
            presentUnavailableActionError(action)
        }
    }

    func canPerform(_ action: BHEWorkspaceAction) -> Bool {
        switch action {
        case .extractSelected:
            selectedEntry?.canExtract == true && sourceKind?.isEGame != true
        case .generatePreview:
            selectedEntry != nil
        case .openTheatre:
            previewKind == .modelScene || previewKind == .rasterImage || previewKind == .audio
        case .quickLookPreview:
            currentPreviewURL != nil
        case .export3DAsset:
            canExportSelectedEGameCar
        case .exportShopTextures:
            canExportSelectedEGameShopTextures
        case .extractContainer:
            hasWorkspace && sourceKind?.isEGame != true && selectedGroupID != "all" && filteredEntries.contains { $0.canExtract }
        case .validateReplacement, .createPatchedCopy:
            selectedEntry?.canReplace == true
        case .revealLastOutput:
            lastOutputURL != nil
        case .verifyISO:
            hasWorkspace
        case .exportOperationLog:
            hasWorkspace
        case .showOriginalLocation:
            selectedEntry != nil
        }
    }

    nonisolated func canExportEGameCar(_ entry: BHEEntry) -> Bool {
        entry.isExportableEGameModel
    }

    nonisolated func canExportEGameShopTextures(_ entry: BHEEntry) -> Bool {
        entry.isExportableEGameShopTextures
    }

    func helpText(for action: BHEWorkspaceAction) -> String {
        switch action {
        case .extractSelected:
            selectedEntry?.canExtract == true
            ? "Export the selected texture as a PNG without modifying the ISO."
            : sourceKind?.isEGame == true
                ? "Use Export 3D Asset for supported Road Trip / HG2 / HG3 car body rows."
            : "Select a supported texture to export it as PNG."
        case .generatePreview:
            selectedEntry == nil
            ? "Select a part before generating a preview."
            : "Ask the backend to create the best safe preview it can for the selected part."
        case .openTheatre:
            canPerform(.openTheatre)
            ? "Open the generated preview in a larger inspection surface."
            : "Generate a model, image, or playable audio preview first."
        case .quickLookPreview:
            currentPreviewURL == nil
            ? "Generate a previewable file before using Quick Look."
            : "Use macOS Quick Look for the generated preview file."
        case .export3DAsset:
            canExportSelectedEGameCar
            ? "Export the selected Road Trip / HG2 / HG3 car body as OBJ, MTL, and PNG files into a chosen folder."
            : unsupportedEGameCarExportReason
        case .exportShopTextures:
            canExportSelectedEGameShopTextures
            ? "Export the selected Road Trip / HG2 shop textures as PNG files into a chosen folder."
            : unsupportedEGameShopTextureExportReason
        case .extractContainer:
            sourceKind?.isEGame == true
            ? "Road Trip / HG2 / HG3 batch extraction is not wired through the backend yet."
            : selectedGroupID == "all"
            ? "Select a CPK container to export its supported textures."
            : "Export every supported texture in the selected CPK container."
        case .validateReplacement:
            selectedEntry?.canReplace == true
            ? "Check whether a PNG can replace the selected texture safely."
            : "Select a replaceable APT texture to validate a PNG."
        case .createPatchedCopy:
            selectedEntry?.canReplace == true
            ? "Write a validated replacement into a new ISO copy. The original ISO is not modified."
            : "Validate a replacement PNG before creating a patched ISO copy."
        case .revealLastOutput:
            lastOutputURL == nil
            ? "Export or patch a file before revealing it in Finder."
            : "Show the most recent export or patched ISO in Finder."
        case .verifyISO:
            hasWorkspace
            ? "Check the open ISO for supported containers and known risk markers."
            : "Open an ISO before verifying it."
        case .exportOperationLog:
            hasWorkspace
            ? "Save the current operation log for troubleshooting and records."
            : "Open an ISO before exporting an operation log."
        case .showOriginalLocation:
            selectedEntry == nil
            ? "Select an entry to copy its original offset."
            : "Copy the selected entry's original ISO offset."
        }
    }

    func copySelectedName() {
        guard let selectedEntry else {
            presentNeedsSelectionError()
            return
        }
        copyToPasteboard(selectedEntry.name)
        statusMessage = "Copied name for \(selectedEntry.name)."
    }

    func copySelectedOffset() {
        guard let selectedEntry else {
            presentNeedsSelectionError()
            return
        }
        copyToPasteboard(selectedEntry.offsetText)
        statusMessage = "Copied offset for \(selectedEntry.name)."
    }

    func copySelectedIdentifier() {
        guard let selectedEntry else {
            presentNeedsSelectionError()
            return
        }
        copyToPasteboard(selectedEntry.id)
        statusMessage = "Copied identifier for \(selectedEntry.name)."
    }

    func copyManifestJSON() {
        guard let manifest = selectedPreviewManifest ?? previewManifest else {
            presentUnsupportedSourceError(
                title: "No Manifest Available",
                explanation: "Generate a preview or export before copying manifest JSON.",
                suggestion: nil,
                technicalDetails: selectedEntry?.id
            )
            return
        }

        do {
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            let data = try encoder.encode(manifest)
            guard let json = String(data: data, encoding: .utf8) else {
                throw BHEBackendError.invalidResponse("Manifest JSON could not be encoded as UTF-8.")
            }
            copyToPasteboard(json)
            statusMessage = "Copied manifest JSON."
        } catch {
            let userFacingError = makeUserFacingError(from: error)
            userError = userFacingError
            statusMessage = userFacingError.statusSummary
        }
    }

    func copyTechnicalDetails() {
        var lines: [String] = []
        if let selectedEntry {
            lines.append("entryID: \(selectedEntry.id)")
            lines.append("name: \(selectedEntry.name)")
        }
        if let sourceKind {
            lines.append("sourceKind: \(sourceKind.rawValue)")
        }
        if let selectedPreviewManifest {
            lines.append("operationID: \(selectedPreviewManifest.operationID)")
        }
        if let message = previewState.message {
            lines.append("preview: \(message)")
        }
        if !decoderDiagnostics.isEmpty {
            lines.append(decoderDiagnostics.map { "\($0.title): \($0.detail)" }.joined(separator: "\n"))
        }
        copyToPasteboard(lines.joined(separator: "\n"))
        statusMessage = "Copied technical details."
    }

    func quickLookGeneratedFile(_ file: BHEExportedFile) {
        let url = URL(fileURLWithPath: file.path)
        guard file.previewable, FileManager.default.fileExists(atPath: file.path) else {
            presentUnsupportedSourceError(
                title: "Quick Look Unavailable",
                explanation: "The generated file is missing or is not marked previewable by the backend.",
                suggestion: "Regenerate the preview, then try again.",
                technicalDetails: file.path
            )
            return
        }
        quickLookURL = url
    }

    func revealGeneratedFile(_ file: BHEExportedFile) {
        NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: file.path)])
    }

    func copyGeneratedFilePath(_ file: BHEExportedFile) {
        copyToPasteboard(file.path)
        statusMessage = "Copied generated file path."
    }

    func showVerboseConsole() {
        verboseConsoleOperation = VerboseConsoleOperation(
            id: currentOperationID ?? selectedPreviewManifest?.operationID ?? UUID().uuidString,
            title: selectedEntry?.name ?? "Q's Factory Operation",
            entryID: selectedEntry?.id,
            manifest: selectedPreviewManifest ?? previewManifest,
            diagnostics: decoderDiagnostics,
            relinkReport: materialRelinkReport,
            logEntries: operationLog
        )
    }

    func quickLookCurrentPreview() {
        guard let currentPreviewURL else {
            presentUnsupportedSourceError(
                title: "Quick Look Unavailable",
                explanation: "Generate a previewable file before using Quick Look.",
                suggestion: nil,
                technicalDetails: selectedEntry?.id
            )
            return
        }
        quickLookURL = currentPreviewURL
    }

    func openTheatreForCurrentPreview() {
        guard let selectedEntry else {
            presentNeedsSelectionError()
            return
        }
        theatrePreviewItem = TheatrePreviewItem(
            id: "\(selectedEntry.id)-\(currentOperationID ?? UUID().uuidString)",
            entryID: selectedEntry.id,
            title: selectedEntry.name,
            kind: previewKind,
            url: currentPreviewURL,
            manifest: selectedPreviewManifest ?? previewManifest
        )
    }

    var currentPreviewURL: URL? {
        switch previewKind {
        case .modelScene:
            previewModelURL ?? selectedPreviewManifest?.previewModelURL
        case .rasterImage:
            previewImageURL ?? selectedPreviewManifest?.previewImageURL
        case .audio:
            activeAudioItem?.playableURL
        case .quickLookFile:
            selectedPreviewManifest?.primaryPreviewURL
        case .none, .metadataOnly, .audioCandidate, .unsupported:
            nil
        }
    }

    func openDesignNotes() {
        openLocalProjectDocument(
            relativePath: "docs/MAC_APP_INTERACTION_DESIGN.md",
            title: "Interaction Design Notes Not Found"
        )
    }

    func openDependencyHelp() {
        openLocalProjectDocument(
            relativePath: "docs/QS_FACTORY_STATUS_AND_ROADMAP.md",
            title: "Dependency Help Not Found"
        )
    }

    func showAboutPanel() {
        let alert = NSAlert()
        alert.messageText = "Q's Factory"
        alert.informativeText = """
        Native macOS conversion by catsandsoup.

        With thanks to:
        killercracker for the 3DS Max script.
        Acewell for the BMS script.
        e-Game (JP) for making a very interesting game that I and many others have spent many hours playing.
        The Choro Q Universe Discord server for the support, ideas, and encouragement to start working on things I would have skipped.
        mholeys for combining the Road Trip Adventure / Choro-Q HG2 model and texture extractor merged into this app.

        https://github.com/mholeys/roadtrip-choroq-tools
        """
        alert.addButton(withTitle: "Done")
        alert.runModal()
    }

    func showBackendDiagnostics() {
        isBackendDiagnosticsPresented = true
        Task { await refreshBackendDiagnostics() }
    }

    func refreshBackendDiagnostics() async {
        isBackendDiagnosticsLoading = true
        defer { isBackendDiagnosticsLoading = false }

        do {
            async let version = backend.version()
            async let health = backend.healthCheck()
            async let supportedTypes = backend.listSupportedTypes()
            backendVersion = try await version
            backendHealth = try await health
            self.supportedTypes = try await supportedTypes
            availableBackendCommands = Set(backendVersion?.commands ?? [])

            if let missing = backendHealth?.missingRequiredDependencies, !missing.isEmpty {
                statusMessage = "Backend diagnostics found missing required Python modules: \(missing.map(\.name).joined(separator: ", "))."
                recordOperation(
                    level: .warning,
                    title: "Backend diagnostics found missing required modules",
                    details: missing.map { "\($0.name) (\($0.module))" }.joined(separator: "\n")
                )
            } else {
                statusMessage = "Backend diagnostics completed."
                recordOperation(level: .info, title: "Backend diagnostics completed")
            }
        } catch {
            let userFacingError = makeUserFacingError(from: error)
            userError = userFacingError
            statusMessage = userFacingError.statusSummary
            recordOperation(level: .error, title: userFacingError.title, details: userFacingError.explanation)
        }
    }

    func refreshBackendCommandAvailability() async {
        do {
            let version = try await backend.version()
            backendVersion = version
            availableBackendCommands = Set(version.commands)
        } catch {
            availableBackendCommands = []
        }
    }

    func extractSelectedTexture() async {
        guard let selectedEntry else {
            presentNeedsSelectionError()
            return
        }
        guard selectedEntry.canExtract, selectedEntry.kind == .texture else {
            presentUnavailableActionError(.extractSelected)
            return
        }
        guard let isoURL else {
            presentUnsupportedSourceError(
                title: "Open an ISO First",
                explanation: "Texture extraction needs an open ISO workspace. Your original ISO was not modified.",
                suggestion: "Open a supported ISO, then select a supported APT texture.",
                technicalDetails: nil
            )
            return
        }

        let panel = NSSavePanel()
        panel.allowedContentTypes = [.png]
        panel.canCreateDirectories = true
        panel.message = "Export \(selectedEntry.name) as a PNG. The ISO is opened read-only and will not be modified."
        panel.prompt = "Export PNG"
        panel.nameFieldStringValue = "\(safeFileComponent(selectedEntry.name)).png"

        guard panel.runModal() == .OK, let outputURL = panel.url else {
            return
        }

        isLoading = true
        userError = nil
        statusMessage = "Exporting \(selectedEntry.name)..."
        defer { isLoading = false }

        do {
            let result: BHETextureExtractionResult
            if sourceKind == .discRoot {
                result = try await backend.extractTexture(fromDiscRoot: isoURL, entryID: selectedEntry.id, outputURL: outputURL)
            } else {
                result = try await backend.extractTexture(from: isoURL, entryID: selectedEntry.id, outputURL: outputURL)
            }
            lastOutputURL = URL(fileURLWithPath: result.pngPath)
            let overwriteText = result.overwroteExisting ? " Replaced an existing file." : ""
            statusMessage = "Exported \(selectedEntry.name) to \(lastOutputURL?.lastPathComponent ?? "PNG"). Original ISO was not modified.\(overwriteText)"
            recordOperation(
                level: .info,
                title: "Exported texture",
                details: result.pngPath,
                entryID: selectedEntry.id,
                sourceModified: result.originalISOModified,
                patchedCopyWritten: result.patchedCopyWritten
            )
        } catch {
            let userFacingError = makeUserFacingError(from: error)
            userError = userFacingError
            statusMessage = userFacingError.statusSummary
            recordOperation(level: .error, title: userFacingError.title, details: userFacingError.explanation, entryID: selectedEntry.id)
        }
    }

    func extractSelectedEGameCar() async {
        guard let selectedEntry else {
            presentNeedsSelectionError()
            return
        }
        guard canExportSelectedEGameCar else {
            presentUnsupportedSourceError(
                title: "3D Asset Export Unavailable",
                explanation: unsupportedEGameCarExportReason,
                suggestion: nil,
                technicalDetails: selectedEntry.id
            )
            return
        }
        guard let isoURL else {
            presentUnsupportedSourceError(
                title: "Open a Source First",
                explanation: "3D asset export needs an open Road Trip / HG2 / HG3 workspace. Your original files were not modified.",
                suggestion: "Open a supported ISO or mounted disc root, then select a car body row.",
                technicalDetails: nil
            )
            return
        }

        let panel = NSSavePanel()
        panel.canCreateDirectories = true
        panel.message = "Export \(selectedEntry.name) as OBJ, MTL, and PNG files. The source is read-only and will not be modified."
        panel.prompt = "Export"
        panel.nameFieldStringValue = safeFileComponent(selectedEntry.name)

        guard panel.runModal() == .OK, let outputURL = panel.url else {
            return
        }

        isLoading = true
        userError = nil
        statusMessage = "Exporting \(selectedEntry.name)..."
        defer { isLoading = false }

        do {
            let manifest = try await backend.extractEGameCar(from: isoURL, entryID: selectedEntry.id, outputFolderURL: outputURL)
            try validateSourceImmutability(manifest)
            lastOutputURL = URL(fileURLWithPath: manifest.outputRoot, isDirectory: true)
            applyPreviewManifest(manifest, for: selectedEntry)
            let manifestURL = try writeManifestSidecar(manifest)
            let overwriteText = manifest.overwrittenFiles.isEmpty ? "" : " Replaced \(manifest.overwrittenFiles.count) existing file(s)."
            let warningText = manifest.warnings.isEmpty ? "" : " \(manifest.warnings.joined(separator: " "))"
            let previewText = manifest.primaryPreviewURL.map { " Preview: \($0.lastPathComponent)." } ?? ""
            statusMessage = "Exported \(selectedEntry.name) to \(lastOutputURL?.lastPathComponent ?? "folder"). Manifest: \(manifestURL.lastPathComponent). Source was not modified.\(previewText)\(overwriteText)\(warningText)"
            recordOperation(
                level: manifest.warnings.isEmpty ? .info : .warning,
                title: "Exported 3D asset",
                details: operationDetails(for: manifest, manifestURL: manifestURL),
                entryID: selectedEntry.id,
                sourceModified: manifest.sourceModified,
                patchedCopyWritten: manifest.patchedCopyWritten
            )
        } catch {
            let userFacingError = makeUserFacingError(from: error)
            userError = userFacingError
            statusMessage = userFacingError.statusSummary
            recordOperation(level: .error, title: userFacingError.title, details: userFacingError.explanation, entryID: selectedEntry.id)
        }
    }

    func extractSelectedEGameShopTextures() async {
        guard let selectedEntry else {
            presentNeedsSelectionError()
            return
        }
        guard canExportSelectedEGameShopTextures else {
            presentUnsupportedSourceError(
                title: "Shop Texture Export Unavailable",
                explanation: unsupportedEGameShopTextureExportReason,
                suggestion: nil,
                technicalDetails: selectedEntry.id
            )
            return
        }
        guard let isoURL else {
            presentUnsupportedSourceError(
                title: "Open a Source First",
                explanation: "Shop texture export needs an open Road Trip / HG2 workspace. Your original files were not modified.",
                suggestion: "Open a supported ISO or mounted disc root, then select a supported shop row.",
                technicalDetails: nil
            )
            return
        }

        let panel = NSSavePanel()
        panel.canCreateDirectories = true
        panel.message = "Export \(selectedEntry.name) shop textures as PNG files. The source is read-only and will not be modified."
        panel.prompt = "Export"
        panel.nameFieldStringValue = safeFileComponent(selectedEntry.name)

        guard panel.runModal() == .OK, let outputURL = panel.url else {
            return
        }

        isLoading = true
        userError = nil
        statusMessage = "Exporting \(selectedEntry.name) shop textures..."
        defer { isLoading = false }

        do {
            let manifest = try await backend.extractEGameShopTextures(from: isoURL, entryID: selectedEntry.id, outputFolderURL: outputURL)
            try validateSourceImmutability(manifest)
            lastOutputURL = URL(fileURLWithPath: manifest.outputRoot, isDirectory: true)
            applyPreviewManifest(manifest, for: selectedEntry)
            let manifestURL = try writeManifestSidecar(manifest)
            let overwriteText = manifest.overwrittenFiles.isEmpty ? "" : " Replaced \(manifest.overwrittenFiles.count) existing file(s)."
            let warningText = manifest.warnings.isEmpty ? "" : " \(manifest.warnings.joined(separator: " "))"
            let previewText = manifest.primaryPreviewURL.map { " Preview: \($0.lastPathComponent)." } ?? ""
            statusMessage = "Exported \(manifest.files.count) texture(s) from \(selectedEntry.name) to \(lastOutputURL?.lastPathComponent ?? "folder"). Manifest: \(manifestURL.lastPathComponent). Source was not modified.\(previewText)\(overwriteText)\(warningText)"
            recordOperation(
                level: manifest.warnings.isEmpty ? .info : .warning,
                title: "Exported shop textures",
                details: operationDetails(for: manifest, manifestURL: manifestURL),
                entryID: selectedEntry.id,
                sourceModified: manifest.sourceModified,
                patchedCopyWritten: manifest.patchedCopyWritten
            )
        } catch {
            let userFacingError = makeUserFacingError(from: error)
            userError = userFacingError
            statusMessage = userFacingError.statusSummary
            recordOperation(level: .error, title: userFacingError.title, details: userFacingError.explanation, entryID: selectedEntry.id)
        }
    }

    func loadPreview(for entry: BHEEntry) async {
        if sourceKind?.isEGame == true {
            await loadEGamePreview(for: entry)
            return
        }

        guard entry.kind == .texture else {
            clearPreview()
            previewEntryID = entry.id
            previewFailureMessage = "Preview unavailable for this entry type."
            previewKind = entry.kind == .sound ? .audioCandidate : .metadataOnly
            previewState = .unsupported(reason: previewUnavailableReason(for: entry))
            return
        }

        guard entry.canExtract, entry.support == .supported else {
            clearPreview()
            previewEntryID = entry.id
            previewFailureMessage = previewUnavailableReason(for: entry)
            previewKind = .unsupported
            previewState = .unsupported(reason: previewFailureMessage ?? "No decoder is available for this asset type yet.")
            return
        }

        guard let isoURL else {
            clearPreview()
            previewEntryID = entry.id
            previewFailureMessage = "Open an ISO before generating a texture preview."
            return
        }

        if previewEntryID == entry.id, previewImageURL != nil {
            return
        }

        previewEntryID = entry.id
        previewImageURL = nil
        previewModelURL = nil
        previewFailureMessage = nil
        selectedPreviewManifest = nil
        generatedFiles = []
        previewKind = .rasterImage
        previewStageText = "Decoding graphics..."
        previewState = .preparing(stage: previewStageText)
        isPreviewLoading = true

        do {
            let outputURL = try previewOutputURL(for: entry)
            let result: BHETexturePreviewResult
            if sourceKind == .discRoot {
                result = try await backend.previewTexture(inDiscRoot: isoURL, entryID: entry.id, outputURL: outputURL)
            } else {
                result = try await backend.previewTexture(in: isoURL, entryID: entry.id, outputURL: outputURL)
            }
            guard selectedEntryID == entry.id else {
                return
            }
            previewImageURL = URL(fileURLWithPath: result.pngPath)
            previewFailureMessage = nil
            generatedFiles = [
                BHEExportedFile(
                    path: result.pngPath,
                    kind: "texture",
                    role: "preview",
                    previewable: true,
                    mediaType: "image/png",
                    applied: true,
                    sizeBytes: fileSize(at: URL(fileURLWithPath: result.pngPath)),
                    warning: nil
                )
            ]
            previewState = FileManager.default.fileExists(atPath: result.pngPath)
                ? .ready
                : .failed(message: "Decoded image was reported, but the generated file no longer exists in cache.")
            decoderDiagnostics = [
                DecoderDiagnostic(title: "Decoder", detail: "preview-texture"),
                DecoderDiagnostic(title: "Image", detail: "\(result.width) x \(result.height), alpha \(result.hasAlpha ? "present" : "not detected")")
            ]
        } catch {
            guard selectedEntryID == entry.id else {
                return
            }
            let userFacingError = makeUserFacingError(from: error)
            previewFailureMessage = userFacingError.explanation
            previewState = .failed(message: userFacingError.explanation)
            statusMessage = userFacingError.statusSummary
        }

        if selectedEntryID == entry.id {
            isPreviewLoading = false
        }
    }

    private func performLoad(_ operation: () async throws -> BHEScanResult) async -> Bool {
        isLoading = true
        userError = nil
        missingGUIReport = nil
        clearPreview()
        defer { isLoading = false }

        do {
            let result = try await operation()
            isoSummary = result.iso
            containers = result.containers
            entries = result.entries
            selectedGroupID = "all"
            selectedEntryID = result.entries.first?.id
            await refreshBackendCommandAvailability()
            let noun = result.iso.sourceFamily == "egame" ? "parts" : "entries"
            statusMessage = "Loaded \(result.iso.isoName): \(result.entries.count) \(noun)."
            recordOperation(
                level: .info,
                title: "Loaded source",
                details: "\(result.iso.gameTitle) \(result.iso.variant): \(result.entries.count) \(noun)"
            )
            return true
        } catch {
            let userFacingError = makeUserFacingError(from: error)
            userError = userFacingError
            statusMessage = userFacingError.statusSummary
            recordOperation(level: .error, title: userFacingError.title, details: userFacingError.explanation)
            return false
        }
    }

    private func makeUserFacingError(from error: Error) -> BHEUserFacingError {
        if case BHEBackendError.commandFailed(let payload) = error {
            return BHEUserFacingError(
                title: payload.title,
                explanation: payload.explanation,
                suggestion: payload.suggestion,
                technicalDetails: payload.technicalDetails,
                relatedEntryID: payload.relatedEntryID,
                safeToRetry: payload.safeToRetry,
                originalISOModified: payload.originalISOModified,
                patchedCopyWritten: payload.patchedCopyWritten
            )
        }

        if case BHEBackendError.commandUnavailable(let details) = error {
            return BHEUserFacingError(
                title: "Python Asset Reader Not Found",
                explanation: "The app could not start the Python command that reads Choro-Q BHE assets. Your original ISO was not modified.",
                suggestion: "Build and run the Q's Factory Xcode scheme so the backend is copied into the signed app bundle.",
                technicalDetails: details,
                relatedEntryID: nil,
                safeToRetry: true,
                originalISOModified: false,
                patchedCopyWritten: false
            )
        }

        if case BHEBackendError.invalidResponse(let details) = error,
           details.localizedCaseInsensitiveContains("Operation not permitted"),
           details.localizedCaseInsensitiveContains("bhe_json.py") {
            return BHEUserFacingError(
                title: "Backend Blocked By Sandbox",
                explanation: "The app tried to run a Python bridge outside its signed bundle and macOS blocked that access. Your original files were not modified.",
                suggestion: "Clean and rebuild the Q's Factory Xcode scheme so the bundled backend is present at Contents/Resources/backend.",
                technicalDetails: details,
                relatedEntryID: nil,
                safeToRetry: true,
                originalISOModified: false,
                patchedCopyWritten: false
            )
        }

        return BHEUserFacingError(
            title: "Could Not Open ISO",
            explanation: "The selected source could not be scanned as a supported Choro-Q source. Your original files were not modified.",
            suggestion: "Choose a Barnhouse Effect ISO or mounted folder, or a mounted Road Trip / HG2 / HG3 disc root.",
            technicalDetails: error.localizedDescription,
            relatedEntryID: nil,
            safeToRetry: true,
            originalISOModified: false,
            patchedCopyWritten: false
        )
    }

    private func presentBINCUEGuidance(for url: URL) {
        let directory = url.deletingLastPathComponent()
        let stem = url.deletingPathExtension().lastPathComponent
        let cueURL = url.pathExtension.lowercased() == "cue"
            ? url
            : directory.appendingPathComponent("\(stem).cue")
        let binURL = url.pathExtension.lowercased() == "bin"
            ? url
            : directory.appendingPathComponent("\(stem).bin")
        let basenameURL = directory.appendingPathComponent("\(stem)-converted")
        let isoURL = directory.appendingPathComponent("\(stem)-converted01.iso")

        let command = """
        bchunk \(shellQuoted(binURL.path)) \(shellQuoted(cueURL.path)) \(shellQuoted(basenameURL.path))
        hdiutil attach \(shellQuoted(isoURL.path))
        """
        presentUnsupportedSourceError(
            title: "BIN/CUE Conversion Needed",
            explanation: "The current backend scans ISO files, not raw BIN/CUE pairs. bchunk can convert this pair into a data-track ISO without modifying your original files.",
            suggestion: "Install or bundle bchunk, run the shown command, mount the generated ISO, then open the mounted volume in Q's Factory.",
            technicalDetails: command
        )
        recordOperation(level: .info, title: "Prepared BIN/CUE conversion guidance", details: command)
    }

    private func presentMountedFolderGuidance(for url: URL) {
        presentUnsupportedSourceError(
            title: "Mounted Folder Scanning Not Available Yet",
            explanation: "The selected folder may be a mounted disc volume or extracted disc root, but this backend currently scans ISO files through pycdlib only.",
            suggestion: "For this build, open a supported ISO file. A future scan-disc-root command should make mounted volumes the preferred source path.",
            technicalDetails: "Path: \(url.path)"
        )
    }

    private func presentUnsupportedSourceError(
        title: String,
        explanation: String,
        suggestion: String?,
        technicalDetails: String?
    ) {
        userError = BHEUserFacingError(
            title: title,
            explanation: explanation,
            suggestion: suggestion,
            technicalDetails: technicalDetails,
            relatedEntryID: nil,
            safeToRetry: true,
            originalISOModified: false,
            patchedCopyWritten: false
        )
        statusMessage = userError?.statusSummary ?? statusMessage
    }

    private func presentUnavailableActionError(_ action: BHEWorkspaceAction) {
        userError = BHEUserFacingError(
            title: "\(action.label.replacingOccurrences(of: "...", with: "")) Is Not Available",
            explanation: "This workflow is not available in the Mac app yet. Your original ISO was not modified.",
            suggestion: "Use the existing Python tools for extraction workflows that are already supported.",
            technicalDetails: nil,
            relatedEntryID: selectedEntry?.id,
            safeToRetry: true,
            originalISOModified: false,
            patchedCopyWritten: false
        )
        statusMessage = userError?.statusSummary ?? statusMessage
    }

    private func presentNeedsSelectionError() {
        userError = BHEUserFacingError(
            title: "Select an Entry",
            explanation: "Choose an entry in the asset table before using this command.",
            suggestion: nil,
            technicalDetails: nil,
            relatedEntryID: nil,
            safeToRetry: true,
            originalISOModified: false,
            patchedCopyWritten: false
        )
        statusMessage = userError?.statusSummary ?? statusMessage
    }

    private func revealLastOutput() {
        guard let lastOutputURL else {
            return
        }
        NSWorkspace.shared.activateFileViewerSelecting([lastOutputURL])
    }

    private func exportOperationLog() {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.json]
        panel.canCreateDirectories = true
        panel.message = "Save the current Q's Factory operation log as JSON."
        panel.prompt = "Export Log"
        panel.nameFieldStringValue = "qfactory-operation-log.json"

        guard panel.runModal() == .OK, let outputURL = panel.url else {
            return
        }

        do {
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            encoder.dateEncodingStrategy = .iso8601
            let data = try encoder.encode(operationLog)
            try data.write(to: outputURL, options: .atomic)
            lastOutputURL = outputURL
            statusMessage = "Saved operation log to \(outputURL.lastPathComponent)."
            recordOperation(level: .info, title: "Exported operation log", details: outputURL.path)
        } catch {
            let userFacingError = BHEUserFacingError(
                title: "Could Not Save Operation Log",
                explanation: "Q's Factory could not write the operation log to the selected location.",
                suggestion: "Choose a writable folder and try again.",
                technicalDetails: error.localizedDescription,
                relatedEntryID: nil,
                safeToRetry: true,
                originalISOModified: false,
                patchedCopyWritten: false
            )
            userError = userFacingError
            statusMessage = userFacingError.statusSummary
            recordOperation(level: .error, title: userFacingError.title, details: userFacingError.explanation)
        }
    }

    private func openLocalProjectDocument(relativePath: String, title: String) {
        let currentDirectory = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        let sourceCheckoutRoot = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()

        let candidates = [
            currentDirectory.appendingPathComponent(relativePath),
            sourceCheckoutRoot.appendingPathComponent(relativePath)
        ]

        guard let url = candidates.first(where: { FileManager.default.fileExists(atPath: $0.path) }) else {
            presentUnsupportedSourceError(
                title: title,
                explanation: "The local project document is not available from this build. No installer was run and no system files were changed.",
                suggestion: "Open the repository docs manually, or run diagnostics from a local checkout.",
                technicalDetails: candidates.map(\.path).joined(separator: "\n")
            )
            return
        }

        NSWorkspace.shared.open(url)
    }

    private func copyToPasteboard(_ value: String) {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(value, forType: .string)
    }

    private func clearPreview() {
        previewTask?.cancel()
        previewTask = nil
        previewEntryID = nil
        previewImageURL = nil
        previewModelURL = nil
        previewManifest = nil
        selectedPreviewManifest = nil
        previewKind = .none
        previewState = .idle
        previewStageText = ""
        generatedFiles = []
        currentOperationID = nil
        materialRelinkReport = .empty
        decoderDiagnostics = []
        theatrePreviewItem = nil
        quickLookURL = nil
        isPreviewLoading = false
        previewFailureMessage = nil
    }

    private func refreshMissingGUIReportIfNeeded() async {
        guard sourceKind?.isEGame == true, let isoURL else {
            missingGUIReport = nil
            return
        }
        do {
            let report = try await backend.reportMissingGUIAssets(from: isoURL, representedEntryIDs: entries.map(\.id))
            missingGUIReport = report
            recordOperation(
                level: report.missingFileCount == 0 ? .info : .warning,
                title: "Missing GUI asset report",
                details: "\(report.discoveredFileCount) discovered, \(report.missingFileCount) missing from the current GUI list."
            )
        } catch {
            missingGUIReport = nil
            recordOperation(level: .warning, title: "Missing GUI asset report failed", details: error.localizedDescription)
        }
    }

    private func loadEGamePreview(for entry: BHEEntry) async {
        guard entry.isExportableEGameModel else {
            clearPreview()
            previewEntryID = entry.id
            previewFailureMessage = previewUnavailableReason(for: entry)
            previewKind = entry.kind == .sound ? .audioCandidate : .metadataOnly
            previewState = .unsupported(reason: previewFailureMessage ?? "No decoder is available for this asset type yet.")
            return
        }
        guard availableBackendCommands.contains("preview-egame-car") else {
            clearPreview()
            previewEntryID = entry.id
            previewFailureMessage = "The bundled backend does not expose preview-egame-car yet."
            previewKind = .unsupported
            previewState = .unsupported(reason: previewFailureMessage ?? "No decoder is available for this asset type yet.")
            return
        }
        guard let isoURL else {
            clearPreview()
            previewEntryID = entry.id
            previewFailureMessage = "Open a Road Trip / HG2 / HG3 source before generating a car preview."
            return
        }
        if previewEntryID == entry.id, previewImageURL != nil || previewModelURL != nil {
            return
        }

        previewEntryID = entry.id
        previewImageURL = nil
        previewModelURL = nil
        previewFailureMessage = nil
        previewKind = .modelScene
        previewStageText = "Preparing scene..."
        previewState = .preparing(stage: previewStageText)
        isPreviewLoading = true
        defer {
            if selectedEntryID == entry.id {
                isPreviewLoading = false
            }
        }

        do {
            let outputFolderURL = try previewFolderURL(for: entry)
            let manifest = try await backend.previewEGameCar(from: isoURL, entryID: entry.id, outputFolderURL: outputFolderURL)
            try validateSourceImmutability(manifest)
            guard selectedEntryID == entry.id else {
                return
            }
            applyPreviewManifest(manifest, for: entry)
            if previewImageURL == nil && previewModelURL == nil {
                previewFailureMessage = "The backend exported \(manifest.files.count) preview asset(s), but no native-previewable OBJ or PNG file was returned."
                previewState = .partial(reason: previewFailureMessage ?? "Generated files exist, but no native preview file was selected.")
            }
        } catch {
            guard selectedEntryID == entry.id else {
                return
            }
            let userFacingError = makeUserFacingError(from: error)
            previewFailureMessage = userFacingError.explanation
            previewState = .failed(message: userFacingError.explanation)
            statusMessage = userFacingError.statusSummary
        }
    }

    private func applyPreviewManifest(_ manifest: BHEExportManifest, for entry: BHEEntry) {
        previewEntryID = entry.id
        previewManifest = manifest
        selectedPreviewManifest = manifest
        generatedFiles = manifest.files
        currentOperationID = manifest.operationID
        previewImageURL = manifest.previewImageURL
        previewModelURL = manifest.previewModelURL
        previewFailureMessage = nil
        decoderDiagnostics = diagnostics(for: manifest, entry: entry)
        materialRelinkReport = materialReport(for: manifest)

        if let modelURL = manifest.previewModelURL, FileManager.default.fileExists(atPath: modelURL.path) {
            previewKind = .modelScene
            previewState = manifest.warnings.isEmpty
                ? .ready
                : .partial(reason: manifest.warnings.joined(separator: " "))
            return
        }

        if let imageURL = manifest.previewImageURL, FileManager.default.fileExists(atPath: imageURL.path) {
            previewKind = .rasterImage
            previewState = manifest.warnings.isEmpty
                ? .ready
                : .partial(reason: manifest.warnings.joined(separator: " "))
            return
        }

        if let primaryURL = manifest.primaryPreviewURL, FileManager.default.fileExists(atPath: primaryURL.path) {
            previewKind = .quickLookFile
            previewState = .partial(reason: "Generated preview file is available through Quick Look, but no richer native preview is connected yet.")
            return
        }

        previewKind = .metadataOnly
        previewState = .partial(reason: "The backend returned a manifest, but no generated preview file exists in cache.")
    }

    private func diagnostics(for manifest: BHEExportManifest, entry: BHEEntry) -> [DecoderDiagnostic] {
        var diagnostics = [
            DecoderDiagnostic(title: "Operation", detail: manifest.operationID),
            DecoderDiagnostic(title: "Source Safety", detail: "sourceModified=\(manifest.sourceModified), patchedCopyWritten=\(manifest.patchedCopyWritten)"),
            DecoderDiagnostic(title: "Generated Files", detail: "\(manifest.files.count)")
        ]
        if let role = entry.exportRoleSummary {
            diagnostics.append(DecoderDiagnostic(title: "Expected Output", detail: role))
        }
        if !manifest.warnings.isEmpty {
            diagnostics.append(DecoderDiagnostic(title: "Warnings", detail: manifest.warnings.joined(separator: "\n")))
        }
        return diagnostics
    }

    private func materialReport(for manifest: BHEExportManifest) -> MaterialRelinkReport {
        let textureFiles = manifest.files.filter { $0.kind == "texture" && $0.exists }
        let materialFiles = manifest.files.filter { $0.kind == "material" && $0.exists }
        let warnings = manifest.warnings.filter {
            $0.localizedCaseInsensitiveContains("material")
                || $0.localizedCaseInsensitiveContains("texture")
        }
        return MaterialRelinkReport(
            automaticTextureCount: textureFiles.count,
            manuallyRelinkedMaterialNames: [],
            unresolvedMaterialNames: materialFiles.isEmpty && !textureFiles.isEmpty ? [] : [],
            warnings: warnings
        )
    }

    private func fileSize(at url: URL) -> Int? {
        guard let values = try? url.resourceValues(forKeys: [.fileSizeKey]) else {
            return nil
        }
        return values.fileSize
    }

    private func validateSourceImmutability(_ manifest: BHEExportManifest) throws {
        guard !manifest.sourceModified, !manifest.patchedCopyWritten else {
            throw BHEBackendError.invalidResponse(
                "Backend reported sourceModified=\(manifest.sourceModified), patchedCopyWritten=\(manifest.patchedCopyWritten)."
            )
        }
    }

    private func writeManifestSidecar(_ manifest: BHEExportManifest) throws -> URL {
        let outputRootURL = URL(fileURLWithPath: manifest.outputRoot, isDirectory: true)
        try FileManager.default.createDirectory(at: outputRootURL, withIntermediateDirectories: true)
        let manifestURL = outputRootURL.appendingPathComponent("qfactory-export-manifest.json")
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(manifest)
        try data.write(to: manifestURL, options: .atomic)
        return manifestURL
    }

    private func operationDetails(for manifest: BHEExportManifest, manifestURL: URL) -> String {
        var details = [
            "operationID: \(manifest.operationID)",
            "outputRoot: \(manifest.outputRoot)",
            "manifest: \(manifestURL.path)",
            "files: \(manifest.files.count)"
        ]
        if !manifest.overwrittenFiles.isEmpty {
            details.append("overwrittenFiles: \(manifest.overwrittenFiles.count)")
        }
        if !manifest.warnings.isEmpty {
            details.append("warnings: \(manifest.warnings.joined(separator: " "))")
        }
        return details.joined(separator: "\n")
    }

    private func recordOperation(
        level: BHEOperationLogLevel,
        title: String,
        details: String? = nil,
        entryID: String? = nil,
        sourceModified: Bool = false,
        patchedCopyWritten: Bool = false
    ) {
        operationLog.append(
            BHEOperationLogEntry(
                level: level,
                title: title,
                details: details,
                sourcePath: isoURL?.path,
                entryID: entryID,
                sourceModified: sourceModified,
                patchedCopyWritten: patchedCopyWritten
            )
        )
    }

    private func previewUnavailableReason(for entry: BHEEntry) -> String {
        if sourceKind?.isEGame == true {
            return entry.unsupportedReason
                ?? "Preview is available only for supported Road Trip / HG2 / HG3 car body rows."
        }

        switch entry.support {
        case .compressed:
            return "Compressed entries are visible for inspection but cannot be previewed yet."
        case .exportable:
            return "Generated preview unavailable for this exportable entry."
        case .scanOnly:
            return entry.unsupportedReason ?? "This entry is available for scanning only."
        case .unsupported:
            return entry.unsupportedReason ?? "This entry format is not supported for preview."
        case .readOnly:
            return "This entry is read-only and does not expose a texture preview."
        case .risky:
            return "This texture needs review before the app can generate a preview safely."
        case .unknown:
            return "This entry format is not understood well enough to preview."
        case .supported:
            return "Preview unavailable for this texture."
        }
    }

    private func previewOutputURL(for entry: BHEEntry) throws -> URL {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("ChoroQBHEPreviews", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return directory.appendingPathComponent("\(safeFileComponent(entry.id)).png")
    }

    private func previewFolderURL(for entry: BHEEntry) throws -> URL {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("ChoroQEGamePreviews", isDirectory: true)
            .appendingPathComponent(safeFileComponent(entry.id), isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return directory
    }

    private func safeFileComponent(_ value: String) -> String {
        let sanitized = String(value.map { character in
            if character.isLetter || character.isNumber || character == "-" || character == "_" || character == "." {
                return character
            }
            return "_"
        })
        return sanitized.isEmpty ? "texture" : sanitized
    }

    private func shellQuoted(_ value: String) -> String {
        "'\(value.replacingOccurrences(of: "'", with: "'\\''"))'"
    }

    private func looksLikeEGameDiscRoot(_ url: URL) -> Bool {
        guard let contents = try? FileManager.default.contentsOfDirectory(
            at: url,
            includingPropertiesForKeys: [.isDirectoryKey]
        ) else {
            return false
        }
        let folderNames = Set(contents.compactMap { child -> String? in
            guard (try? child.resourceValues(forKeys: [.isDirectoryKey]).isDirectory) == true else {
                return nil
            }
            return child.lastPathComponent.uppercased()
        })
        return folderNames.contains("COURSE")
            && folderNames.contains("SYS")
            && (folderNames.contains("CAR0") || folderNames.contains("CARS"))
    }

    private func containerSystemImage(for container: BHEContainer) -> String {
        if sourceKind?.isEGame == true {
            switch container.name {
            case "CAR0", "CAR1", "CAR2", "CAR3", "CAR4", "CARS":
                return "car"
            case "COURSE", "ACTION":
                return "road.lanes"
            case "FLD":
                return "map"
            case "SHOP":
                return "storefront"
            case "ITEM", "SYS":
                return "rectangle.stack"
            case "SOUND":
                return "waveform"
            case "ROOT":
                return "externaldrive"
            default:
                return "folder"
            }
        }
        return "shippingbox"
    }
}
