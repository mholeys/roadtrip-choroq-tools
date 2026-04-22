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
    var statusMessage = "Open a PlayStation 2 ISO, BIN/CUE pair, or mounted source folder to start."
    var userError: BHEUserFacingError?
    var lastOutputURL: URL?
    var previewEntryID: BHEEntry.ID?
    var previewImageURL: URL?
    var isPreviewLoading = false
    var previewFailureMessage: String?
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
                title: container.name,
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
        ] + cpkGroups
    }

    var filteredEntries: [BHEEntry] {
        let groupEntries: [BHEEntry]
        if selectedGroupID == "all" {
            groupEntries = entries
        } else {
            groupEntries = entries.filter { $0.containerID == selectedGroupID }
        }

        let supportFiltered = groupEntries.filter { entry in
            if !showCompressedEntries && entry.support == .compressed {
                return false
            }
            if !showUnsupportedEntries && entry.support == .unknown {
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
        }
    }

    func openDiscRoot(at url: URL) async {
        let didLoad = await performLoad {
            try await backend.scanDiscRoot(at: url)
        }
        if didLoad {
            isoURL = url
            sourceKind = isoSummary?.sourceFamily == "egame" ? .egameDiscRoot : .discRoot
        }
    }

    func openEGameDiscRoot(at url: URL) async {
        let didLoad = await performLoad {
            try await backend.scanEGameDiscRoot(at: url)
        }
        if didLoad {
            isoURL = url
            sourceKind = .egameDiscRoot
        }
    }

    func closeISO() {
        isoURL = nil
        sourceKind = nil
        isoSummary = nil
        containers = []
        entries = []
        selectedGroupID = "all"
        selectedEntryID = nil
        searchText = ""
        clearPreview()
        statusMessage = "Closed source. Open another ISO, BIN/CUE pair, or mounted source folder to start."
    }

    func performAction(_ action: BHEWorkspaceAction) {
        switch action {
        case .extractSelected:
            Task { await extractSelectedTexture() }
        case .revealLastOutput:
            revealLastOutput()
        case .showOriginalLocation:
            guard let selectedEntry else {
                presentNeedsSelectionError()
                return
            }
            copyToPasteboard(selectedEntry.offsetText)
            statusMessage = "Copied original location offset for \(selectedEntry.name)."
        case .extractContainer, .validateReplacement, .createPatchedCopy, .verifyISO, .exportOperationLog:
            presentUnavailableActionError(action)
        }
    }

    func canPerform(_ action: BHEWorkspaceAction) -> Bool {
        switch action {
        case .extractSelected:
            selectedEntry?.canExtract == true && sourceKind?.isEGame != true
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

    func helpText(for action: BHEWorkspaceAction) -> String {
        switch action {
        case .extractSelected:
            selectedEntry?.canExtract == true
            ? "Export the selected texture as a PNG without modifying the ISO."
            : sourceKind?.isEGame == true
                ? "Road Trip / HG2 / HG3 extraction is visible as read-only scan data until model export is wired through the backend."
                : "Select a supported texture to export it as PNG."
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

    func openDesignNotes() {
        let url = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
            .appendingPathComponent("docs/MAC_APP_INTERACTION_DESIGN.md")
        NSWorkspace.shared.activateFileViewerSelecting([url])
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

            if let missing = backendHealth?.missingRequiredDependencies, !missing.isEmpty {
                statusMessage = "Backend diagnostics found missing required Python modules: \(missing.map(\.name).joined(separator: ", "))."
            } else {
                statusMessage = "Backend diagnostics completed."
            }
        } catch {
            let userFacingError = makeUserFacingError(from: error)
            userError = userFacingError
            statusMessage = userFacingError.statusSummary
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
        } catch {
            let userFacingError = makeUserFacingError(from: error)
            userError = userFacingError
            statusMessage = userFacingError.statusSummary
        }
    }

    func loadPreview(for entry: BHEEntry) async {
        guard entry.kind == .texture else {
            clearPreview()
            previewEntryID = entry.id
            previewFailureMessage = "Preview unavailable for this entry type."
            return
        }

        guard entry.canExtract, entry.support == .supported else {
            clearPreview()
            previewEntryID = entry.id
            previewFailureMessage = previewUnavailableReason(for: entry)
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
        previewFailureMessage = nil
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
        } catch {
            guard selectedEntryID == entry.id else {
                return
            }
            let userFacingError = makeUserFacingError(from: error)
            previewFailureMessage = userFacingError.explanation
            statusMessage = userFacingError.statusSummary
        }

        if selectedEntryID == entry.id {
            isPreviewLoading = false
        }
    }

    private func performLoad(_ operation: () async throws -> BHEScanResult) async -> Bool {
        isLoading = true
        userError = nil
        clearPreview()
        defer { isLoading = false }

        do {
            let result = try await operation()
            isoSummary = result.iso
            containers = result.containers
            entries = result.entries
            selectedGroupID = "all"
            selectedEntryID = result.entries.first?.id
            let noun = result.iso.sourceFamily == "egame" ? "parts" : "entries"
            statusMessage = "Loaded \(result.iso.isoName): \(result.entries.count) \(noun)."
            return true
        } catch {
            let userFacingError = makeUserFacingError(from: error)
            userError = userFacingError
            statusMessage = userFacingError.statusSummary
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

    private func copyToPasteboard(_ value: String) {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(value, forType: .string)
    }

    private func clearPreview() {
        previewEntryID = nil
        previewImageURL = nil
        isPreviewLoading = false
        previewFailureMessage = nil
    }

    private func previewUnavailableReason(for entry: BHEEntry) -> String {
        if sourceKind?.isEGame == true {
            return "Road Trip / HG2 / HG3 parts are scan-only in this build. Model preview and extraction are not wired through the backend yet."
        }

        switch entry.support {
        case .compressed:
            return "Compressed entries are visible for inspection but cannot be previewed yet."
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
            default:
                return "folder"
            }
        }
        return "shippingbox"
    }
}
