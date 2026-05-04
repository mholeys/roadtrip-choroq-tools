import SwiftUI

struct EntryDetailView: View {
    @Bindable var store: BHEWorkspaceStore

    var body: some View {
        Group {
            if let entry = store.selectedEntry {
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        DetailHeader(
                            entry: entry,
                            supportDisplay: EntrySupportDisplay(
                                entry: entry,
                                canExport3D: store.canExportEGameCar(entry),
                                isEGameSource: store.sourceKind?.isEGame == true
                            )
                        )

                        PreviewCardView(store: store, entry: entry)

                        PreviewStatusView(store: store, entry: entry)

                        AssetCapabilityView(
                            entry: entry,
                            sourceKind: store.sourceKind,
                            canExport3D: store.canExportEGameCar(entry),
                            unsupportedExportReason: store.unsupportedEGameCarExportReason
                        )

                        WorkshopSection(title: "Part Specs", systemImage: "list.bullet.rectangle") {
                            MetadataGrid(entry: entry)
                        }

                        if !store.generatedFiles.isEmpty {
                            GeneratedFilesView(store: store)
                        }

                        if store.sourceKind?.isEGame == true {
                            AssetRelationshipsView(entry: entry, manifest: store.previewEntryID == entry.id ? store.previewManifest : nil)
                            MissingGUIReportView(report: store.missingGUIReport)
                        }

                        DecoderDetailsView(store: store)

                        WorkshopSection(title: "Service Actions", systemImage: "wrench.adjustable") {
                            ContextualActionsView(store: store, entry: entry)
                        }
                        .controlSize(.regular)
                    }
                    .padding(22)
                    .frame(maxWidth: 620, alignment: .leading)
                }
                .task(id: entry.id) {
                    if entry.kind == .texture || entry.kind == .model || entry.kind == .shop || entry.kind == .graphics || entry.kind == .sound {
                        await store.loadPreview(for: entry)
                    }
                }
            } else {
                ContentUnavailableView(
                    "Select a Part",
                    systemImage: "sidebar.left",
                    description: Text("Choose an asset to inspect previews, part specs, offsets, format details, and safe actions.")
                )
            }
        }
        .navigationTitle("Part Inspector")
    }
}

private struct PreviewCardView: View {
    let store: BHEWorkspaceStore
    let entry: BHEEntry

    var body: some View {
        Group {
            switch currentKind {
            case .modelScene:
                ScenePreviewView(
                    entry: entry,
                    modelURL: store.previewEntryID == entry.id ? store.previewModelURL : nil,
                    manifest: store.selectedPreviewManifest,
                    previewState: store.previewState,
                    isLoading: store.previewEntryID == entry.id && store.isPreviewLoading,
                    failureMessage: store.previewEntryID == entry.id ? store.previewFailureMessage : nil,
                    relinkReport: store.materialRelinkReport
                )
            case .rasterImage:
                RasterPreviewView(
                    entry: entry,
                    background: store.previewBackground,
                    previewURL: store.previewEntryID == entry.id ? store.previewImageURL : nil,
                    previewState: store.previewState,
                    isLoading: store.previewEntryID == entry.id && store.isPreviewLoading,
                    failureMessage: store.previewEntryID == entry.id ? store.previewFailureMessage : nil
                )
            case .audio, .audioCandidate:
                AudioPreviewView(entry: entry, item: store.activeAudioItem, playbackState: store.playbackState, previewState: store.previewState)
            case .quickLookFile:
                QuickLookFilePreviewCard(store: store, entry: entry)
            case .metadataOnly, .none, .unsupported:
                AssetInspectionSummaryView(
                    entry: entry,
                    sourceKind: store.sourceKind,
                    canExport3D: store.canExportEGameCar(entry),
                    unsupportedExportReason: store.unsupportedEGameCarExportReason
                )
            }
        }
        .frame(maxWidth: .infinity)
    }

    private var currentKind: AssetPreviewKind {
        store.previewEntryID == entry.id ? store.previewKind : defaultKind
    }

    private var defaultKind: AssetPreviewKind {
        switch entry.kind {
        case .model where store.sourceKind?.isEGame == true:
            .modelScene
        case .texture, .graphics, .shop:
            .rasterImage
        case .sound:
            .audioCandidate
        default:
            .metadataOnly
        }
    }
}

private struct PreviewStatusView: View {
    let store: BHEWorkspaceStore
    let entry: BHEEntry

    var body: some View {
        WorkshopSection(title: "Preview Status", systemImage: status.systemImage) {
            VStack(alignment: .leading, spacing: 8) {
                Label(statusTitle, systemImage: status.systemImage)
                    .font(.callout.weight(.semibold))
                    .foregroundStyle(tint)
                Text(statusMessage)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var status: AssetPreviewState {
        store.previewEntryID == entry.id ? store.previewState : .idle
    }

    private var statusTitle: String {
        switch (store.previewKind, status) {
        case (.modelScene, .ready):
            return store.materialRelinkReport.automaticTextureCount > 0 ? "Textured preview" : "Geometry only"
        case (.rasterImage, .ready):
            return "Image decoded"
        case (.audio, .ready):
            return "Audio playable"
        case (.audioCandidate, _):
            return "Audio candidate"
        default:
            return status.title
        }
    }

    private var statusMessage: String {
        if let message = status.message {
            return message
        }
        switch store.previewKind {
        case .modelScene:
            return store.materialRelinkReport.automaticTextureCount > 0
                ? "Mesh and generated texture files are available for native SceneKit preview."
                : "Geometry loaded. Texture data was not resolved for this asset."
        case .rasterImage:
            return "Generated image file is available for inspector preview, Quick Look, and export."
        case .audio:
            return "Converted audio is ready for AVFoundation playback."
        case .audioCandidate:
            return "Audio candidate found. No playback decoder is available yet."
        case .quickLookFile:
            return "Generated file is available through macOS Quick Look."
        case .metadataOnly, .none:
            return "Metadata is available. No decoder is connected for a richer preview yet."
        case .unsupported:
            return "No decoder is available for this asset type yet."
        }
    }

    private var tint: Color {
        switch status {
        case .ready:
            QFactoryTheme.serviceGreen
        case .partial, .preparing:
            QFactoryTheme.hazardYellow
        case .failed, .unsupported:
            .secondary
        case .idle:
            QFactoryTheme.factoryBlue
        }
    }
}

private struct DetailHeader: View {
    let entry: BHEEntry
    let supportDisplay: EntrySupportDisplay

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(entry.kind.displayName, systemImage: entry.kind.systemImage)
                .font(.subheadline)
                .foregroundStyle(QFactoryTheme.factoryBlue)

            Text(entry.name)
                .font(.title2.weight(.semibold))
                .textSelection(.enabled)

            Label(supportDisplay.title, systemImage: supportDisplay.systemImage)
                .font(.callout)
                .foregroundStyle(supportDisplay.tint)
        }
    }
}

private struct AssetInspectionSummaryView: View {
    let entry: BHEEntry
    let sourceKind: BHESourceKind?
    let canExport3D: Bool
    let unsupportedExportReason: String

    var body: some View {
        WorkshopSection(title: "Inspection Preview", systemImage: entry.kind.systemImage) {
            VStack(spacing: 10) {
                Image(systemName: entry.kind.systemImage)
                    .font(.system(size: 36, weight: .regular))
                    .foregroundStyle(QFactoryTheme.factoryBlue)
                Text(summaryTitle)
                    .font(.headline)
                Text(summaryBody)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
                if let outputText {
                    Text(outputText)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 20)
        }
        .accessibilityElement(children: .combine)
    }

    private var summaryTitle: String {
        switch entry.kind {
        case .model where canExport3D:
            return "Car model export available"
        case .model:
            return "Model metadata available"
        case .course, .field:
            return "Scene metadata available"
        case .part:
            return "Part metadata available"
        case .apt, .cpk:
            return "Container metadata available"
        case .lzs:
            return "Compressed payload"
        case .shop where entry.isExportableEGameShopTextures:
            return "Shop texture export available"
        case .graphics:
            return "Graphics metadata available"
        case .sound:
            return "Sound metadata available"
        case .shop, .text, .unknown:
            return "Metadata available"
        case .texture:
            return "Texture preview unavailable"
        }
    }

    private var summaryBody: String {
        switch entry.kind {
        case .model:
            return "This row describes a car or model record. Q's Factory can inspect its format, source bay, size, and any mesh or texture counts reported by the backend."
        case .course, .field:
            return "This row describes a world or course record. Q's Factory can inspect its format, source bay, size, and any mesh or texture counts reported by the backend."
        case .part:
            return "This row describes a vehicle or shared part record. Q's Factory can inspect its format, source bay, offset, and size."
        case .apt, .cpk:
            return "This row is a container. Select a supported child texture row when you need an image preview or PNG export."
        case .lzs:
            return "This row is compressed. It needs decompression support before preview, replacement, or export can be offered safely."
        case .shop where entry.isExportableEGameShopTextures:
            return "This row contains Road Trip / HG2 town shop textures. Q's Factory can export decoded PNG files from this supported shop BIN."
        case .graphics:
            return "This row is a graphics candidate. Q's Factory lists its source path, size, format, and current backend support without claiming a decoded texture preview."
        case .sound:
            return "This row is a sound or audio candidate. Q's Factory lists it even when conversion and playback are not implemented yet."
        case .shop, .text, .unknown:
            return "This row is available for inspection. Preview and export need a typed backend reader for this specific format."
        case .texture:
            return "This texture does not currently expose a generated PNG preview."
        }
    }

    private var outputText: String? {
        switch entry.kind {
        case .model where canExport3D:
            return "Expected outputs: OBJ mesh, MTL material library, and PNG diffuse texture when the source row contains texture data."
        case .shop where entry.isExportableEGameShopTextures:
            return "Expected outputs: one PNG per decoded shop texture."
        case .sound:
            return "Audio preview requires a backend conversion to a macOS-playable file. VAG, TSQ, and TVB are currently scanned only."
        case .graphics:
            return "Graphics export requires a typed decoder for this container. GSL/E3D/ICO records are currently scanned only unless another specific command is wired."
        case .model where sourceKind?.isEGame == true:
            return unsupportedExportReason
        case .model:
            return "No model export is connected for this format yet."
        default:
            return nil
        }
    }
}

private struct AssetCapabilityView: View {
    let entry: BHEEntry
    let sourceKind: BHESourceKind?
    let canExport3D: Bool
    let unsupportedExportReason: String

    var body: some View {
        WorkshopSection(title: "Asset Role", systemImage: "info.circle") {
            VStack(alignment: .leading, spacing: 10) {
                CapabilityRow(label: "Description", value: containsText)
                CapabilityRow(label: "Displays", value: displaysText)
                CapabilityRow(label: "macOS Native", value: nativeDisplayText)
                CapabilityRow(label: "Exports", value: exportText)
            }
        }
    }

    private var containsText: String {
        switch entry.kind {
        case .texture:
            return "Decoded APT texture data: pixel payload, dimensions, palette metadata, and optional alpha."
        case .apt:
            return "APT texture container metadata. Individual textures inside it become previewable texture rows when supported."
        case .model:
            if sourceKind?.isEGame == true {
                return "Road Trip / HG2 / HG3 model record. These files usually combine mesh chunks, UVs, colours, and texture blocks."
            }
            return "Barnhouse Effect model record such as PBL, MPD, HPD, or MPC. These formats carry mesh data and texture references."
        case .part:
            return "Vehicle or part record from the source layout. It is listed for inspection until a typed extractor is connected."
        case .course, .field:
            return "Course or field record. These can include scene meshes, collision data, map pieces, and texture blocks."
        case .shop:
            return entry.isExportableEGameShopTextures
                ? "Road Trip / HG2 town shop texture BIN from the named SHOP section."
                : "Shop or game-data record from the source layout."
        case .graphics:
            return "System, item, title, map, score, font, icon, or menu graphics candidate from the Road Trip / HG2 / HG3 source layout."
        case .sound:
            return "Sound, music sequence, sound bank, driver, or PlayStation ADPCM candidate from the Road Trip / HG2 / HG3 source layout."
        case .text:
            return "Text, table, or font-related record. The app currently lists its location and size."
        case .lzs:
            return "Compressed LZS payload. It needs decompression support before preview or replacement is safe."
        case .cpk:
            return "CPK archive container record with offsets to subfiles."
        case .unknown:
            return "Unknown binary record. Q's Factory can preserve its location and size for reverse-engineering."
        }
    }

    private var displaysText: String {
        switch entry.kind {
        case .texture:
            return entry.canExtract ? "Preview and PNG export are available for supported APT textures." : "Metadata only until this texture is safe to decode."
        case .model, .course, .field, .part:
            return "Metadata inspection now. Native 3D display needs conversion to a SceneKit, Model I/O, OBJ, or USDZ representation."
        case .apt, .cpk:
            return "Container metadata. Select a child texture row for image preview."
        case .lzs:
            return "Compressed metadata only."
        case .shop:
            return entry.isExportableEGameShopTextures ? "PNG export is available for supported town shop texture rows." : "Metadata only."
        case .graphics:
            return "Metadata only until a graphics decoder/export command supports this exact format."
        case .sound:
            return "Metadata only until a sound decoder/conversion command supports this exact format."
        case .text, .unknown:
            return "Metadata only."
        }
    }

    private var nativeDisplayText: String {
        switch entry.kind {
        case .texture:
            return "Yes after backend decoding: SwiftUI displays the generated PNG with NSImage."
        case .model, .course, .field, .part:
            return "Not raw. macOS can display OBJ, USDZ, SceneKit scenes, or Model I/O meshes after conversion."
        case .shop where entry.isExportableEGameShopTextures:
            return "Yes after backend decoding: SwiftUI displays the generated PNG with NSImage."
        case .sound:
            return "Not yet. AVFoundation playback requires a generated WAV, AIFF, CAF, or other playable audio file."
        case .graphics:
            return "Not yet. SwiftUI can display generated PNG/TIFF/JPEG output once the backend decodes this format."
        case .apt, .cpk, .lzs, .text, .shop, .unknown:
            return "Not directly. These are custom game/archive formats and need backend parsing first."
        }
    }

    private var exportText: String {
        switch entry.kind {
        case .texture:
            return entry.canExtract ? "PNG file at the user-selected destination." : "No export for this texture yet."
        case .model where sourceKind?.isEGame == true && canExport3D:
            return "OBJ and MTL mesh files plus a PNG diffuse texture when the car record contains one."
        case .model where sourceKind?.isEGame == true:
            return unsupportedExportReason
        case .model, .course, .field, .part:
            return sourceKind?.isEGame == true ? unsupportedExportReason : "No model export is connected for this format yet."
        case .shop where entry.isExportableEGameShopTextures:
            return "PNG files at the user-selected destination."
        case .sound:
            return "No audio export in this phase. The file remains visible as an unsupported or possible audio asset."
        case .graphics:
            return "No graphics export in this phase unless a specific backend command is added for this format."
        case .apt, .cpk, .lzs, .text, .shop, .unknown:
            return "No export in this phase."
        }
    }
}

private struct EntrySupportDisplay {
    let title: String
    let systemImage: String
    let tint: Color

    init(entry: BHEEntry, canExport3D: Bool, isEGameSource: Bool) {
        if canExport3D {
            title = "3D Export"
            systemImage = BHEWorkspaceAction.export3DAsset.systemImage
            tint = QFactoryTheme.serviceGreen
        } else if entry.isExportableEGameShopTextures {
            title = "PNG Export"
            systemImage = BHEWorkspaceAction.exportShopTextures.systemImage
            tint = QFactoryTheme.serviceGreen
        } else if entry.canExtract && !isEGameSource {
            title = "PNG Export"
            systemImage = BHEWorkspaceAction.extractSelected.systemImage
            tint = QFactoryTheme.serviceGreen
        } else if entry.canReplace {
            title = "Replaceable"
            systemImage = BHEWorkspaceAction.validateReplacement.systemImage
            tint = QFactoryTheme.serviceGreen
        } else {
            switch entry.support {
            case .readOnly:
                title = "Inspect"
                systemImage = "eye"
                tint = QFactoryTheme.supportTint(for: entry.support)
            case .risky:
                title = "Needs Review"
                systemImage = entry.support.systemImage
                tint = QFactoryTheme.supportTint(for: entry.support)
            default:
                title = entry.support.displayName
                systemImage = entry.support.systemImage
                tint = QFactoryTheme.supportTint(for: entry.support)
            }
        }
    }
}

private struct GeneratedFilesView: View {
    let store: BHEWorkspaceStore

    var body: some View {
        WorkshopSection(title: "Generated Preview Files", systemImage: "doc.badge.gearshape") {
            VStack(alignment: .leading, spacing: 10) {
                ForEach(store.generatedFiles, id: \.path) { file in
                    HStack(alignment: .firstTextBaseline, spacing: 10) {
                        Image(systemName: icon(for: file))
                            .foregroundStyle(file.exists ? QFactoryTheme.factoryBlue : .secondary)
                            .frame(width: 18)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(file.fileName)
                                .font(.callout.weight(.medium))
                                .lineLimit(1)
                            Text("\(file.kind) - \(file.role) - \(file.pathExtension)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Text(file.path)
                                .font(.caption2.monospaced())
                                .foregroundStyle(.tertiary)
                                .lineLimit(1)
                        }
                        Spacer()
                        Label(file.exists ? "Exists" : "Missing", systemImage: file.exists ? "checkmark.circle" : "xmark.circle")
                            .font(.caption)
                            .foregroundStyle(file.exists ? QFactoryTheme.serviceGreen : .secondary)
                        Button {
                            store.quickLookGeneratedFile(file)
                        } label: {
                            Image(systemName: "eye")
                        }
                        .buttonStyle(.borderless)
                        .disabled(!(file.previewable && file.exists))
                        .help("Quick Look")

                        Button {
                            store.revealGeneratedFile(file)
                        } label: {
                            Image(systemName: "finder")
                        }
                        .buttonStyle(.borderless)
                        .disabled(!file.exists)
                        .help("Reveal in Finder")

                        Button {
                            store.copyGeneratedFilePath(file)
                        } label: {
                            Image(systemName: "doc.on.doc")
                        }
                        .buttonStyle(.borderless)
                        .help("Copy Path")
                    }
                }
                if let manifest = store.selectedPreviewManifest, !manifest.warnings.isEmpty {
                    Divider()
                    ForEach(manifest.warnings, id: \.self) { warning in
                        Label(warning, systemImage: "exclamationmark.triangle")
                            .font(.caption)
                            .foregroundStyle(QFactoryTheme.hazardYellow)
                    }
                }
            }
        }
    }

    private func icon(for file: BHEExportedFile) -> String {
        switch file.kind {
        case "model": "cube"
        case "material": "paintpalette"
        case "texture": "photo"
        case "audio": "waveform"
        default: "doc"
        }
    }
}

private struct QuickLookFilePreviewCard: View {
    let store: BHEWorkspaceStore
    let entry: BHEEntry

    var body: some View {
        WorkshopSection(title: "Generated File", systemImage: "eye") {
            VStack(spacing: 12) {
                Image(systemName: entry.kind.systemImage)
                    .font(.system(size: 34, weight: .regular))
                    .foregroundStyle(QFactoryTheme.factoryBlue)
                Text("Generated file available")
                    .font(.headline)
                Text(store.currentPreviewURL?.lastPathComponent ?? "Use Quick Look to inspect the generated file.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                Button {
                    store.quickLookCurrentPreview()
                } label: {
                    Label("Quick Look Preview", systemImage: "eye")
                }
                .buttonStyle(.borderedProminent)
                .disabled(store.currentPreviewURL == nil)
            }
            .frame(maxWidth: .infinity, minHeight: 220)
            .padding(.vertical, 20)
        }
    }
}

private struct AudioPreviewView: View {
    let entry: BHEEntry
    let item: AssetAudioItem?
    let playbackState: PlaybackState
    let previewState: AssetPreviewState

    var body: some View {
        WorkshopSection(title: "Audio Preview", systemImage: "waveform") {
            VStack(spacing: 12) {
                Image(systemName: item?.playableURL == nil ? "waveform.badge.magnifyingglass" : "play.circle")
                    .font(.system(size: 36, weight: .regular))
                    .foregroundStyle(item?.playableURL == nil ? QFactoryTheme.toolSteel : QFactoryTheme.serviceGreen)
                Text(item?.playableURL == nil ? "Audio candidate" : "Playable audio generated")
                    .font(.headline)
                Text(message)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .frame(maxWidth: .infinity, minHeight: 220)
            .padding(.vertical, 20)
        }
        .accessibilityLabel(item?.playableURL == nil ? "Unsupported audio candidate" : "Audio preview for \(entry.name)")
    }

    private var message: String {
        if let playableURL = item?.playableURL {
            return "Converted to \(playableURL.pathExtension.uppercased()) for AVFoundation playback."
        }
        return previewState.message ?? "This appears to be a sound or music record, but no supported converter is connected yet."
    }
}

private struct DecoderDetailsView: View {
    let store: BHEWorkspaceStore

    var body: some View {
        DisclosureGroup {
            VStack(alignment: .leading, spacing: 8) {
                if !store.decoderDiagnostics.isEmpty {
                    ForEach(store.decoderDiagnostics) { diagnostic in
                        RelationshipRow(label: diagnostic.title, value: diagnostic.detail)
                    }
                } else {
                    Text("No decoder details for this selection yet.")
                        .font(.callout)
                        .foregroundStyle(.secondary)
                }

                if store.materialRelinkReport != .empty {
                    RelationshipRow(label: "Materials", value: store.materialRelinkReport.summary)
                }

                HStack {
                    Button {
                        store.copyTechnicalDetails()
                    } label: {
                        Label("Copy Technical Details", systemImage: "doc.on.doc")
                    }

                    Button {
                        store.copyManifestJSON()
                    } label: {
                        Label("Copy Manifest JSON", systemImage: "curlybraces")
                    }
                    .disabled(store.selectedPreviewManifest == nil)

                    Button {
                        store.showVerboseConsole()
                    } label: {
                        Label("Open Verbose Console", systemImage: "terminal")
                    }
                }
                .buttonStyle(.bordered)
            }
        } label: {
            Label("Decoder Details", systemImage: "text.magnifyingglass")
                .font(.headline)
                .foregroundStyle(QFactoryTheme.factoryBlue)
        }
        .padding()
        .background(QFactoryTheme.panelFill, in: .rect(cornerRadius: 8))
        .overlay {
            RoundedRectangle(cornerRadius: 8)
                .stroke(QFactoryTheme.panelStroke, lineWidth: 1)
        }
    }
}

private struct AssetRelationshipsView: View {
    let entry: BHEEntry
    let manifest: BHEExportManifest?

    var body: some View {
        WorkshopSection(title: "Related Assets", systemImage: "point.3.connected.trianglepath.dotted") {
            VStack(alignment: .leading, spacing: 8) {
                RelationshipRow(label: "Source", value: entry.id)
                if let partSectionNames = entry.partSectionNames, !partSectionNames.isEmpty {
                    RelationshipRow(label: "Sections", value: partSectionNames.joined(separator: ", "))
                }
                if let expectedExportOutputs = entry.expectedExportOutputs, !expectedExportOutputs.isEmpty {
                    RelationshipRow(label: "Expected Output", value: expectedExportOutputs.map { "\($0.role) .\($0.extension)" }.joined(separator: ", "))
                }
                if let manifest {
                    let textureNames = manifest.files.filter { $0.kind == "texture" }.map(\.fileName)
                    let materialNames = manifest.files.filter { $0.kind == "material" }.map(\.fileName)
                    RelationshipRow(label: "Textures", value: textureNames.isEmpty ? textureStatusText : textureNames.joined(separator: ", "))
                    RelationshipRow(label: "Materials", value: materialNames.isEmpty ? "No generated MTL returned." : materialNames.joined(separator: ", "))
                } else {
                    RelationshipRow(label: "Textures", value: textureStatusText)
                    RelationshipRow(label: "Materials", value: materialStatusText)
                }
            }
        }
    }

    private var textureStatusText: String {
        switch entry.kind {
        case .model where entry.isExportableEGameModel:
            "Texture relationship is resolved during preview generation when the car BIN contains texture and CLUT payloads."
        case .shop where entry.isExportableEGameShopTextures:
            "Shop texture relationships are resolved by the shop texture export command."
        case .sound:
            "No texture relationship for audio candidates."
        default:
            entry.unsupportedReason ?? "Texture relationship unknown."
        }
    }

    private var materialStatusText: String {
        entry.isExportableEGameModel ? "OBJ material files are generated with relative PNG texture references when texture data exists." : "No material relationship is known for this asset."
    }
}

private struct RelationshipRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Text(label)
                .font(.callout.weight(.medium))
                .foregroundStyle(.secondary)
                .frame(width: 104, alignment: .leading)
            Text(value)
                .font(.callout)
                .fixedSize(horizontal: false, vertical: true)
                .textSelection(.enabled)
        }
    }
}

private struct MissingGUIReportView: View {
    let report: BHEMissingGUIReport?

    var body: some View {
        WorkshopSection(title: "Missing from GUI", systemImage: "exclamationmark.magnifyingglass") {
            if let report {
                VStack(alignment: .leading, spacing: 8) {
                    Label("\(report.discoveredFileCount) files discovered; \(report.missingFileCount) missing from the current GUI list.", systemImage: report.missingFileCount == 0 ? "checkmark.circle" : "exclamationmark.triangle")
                        .foregroundStyle(report.missingFileCount == 0 ? QFactoryTheme.serviceGreen : QFactoryTheme.hazardYellow)
                    ForEach(report.groups.prefix(6)) { group in
                        Text("\(group.role): \(group.count)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            } else {
                Text("Diagnostic report has not run for this source.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

private struct ContextualActionsView: View {
    let store: BHEWorkspaceStore
    let entry: BHEEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Button {
                    store.performAction(.generatePreview)
                } label: {
                    Label("Generate Preview", systemImage: BHEWorkspaceAction.generatePreview.systemImage)
                }
                .buttonStyle(.borderedProminent)

                Button {
                    store.performAction(.openTheatre)
                } label: {
                    Label("Open Theatre", systemImage: BHEWorkspaceAction.openTheatre.systemImage)
                }
                .disabled(!store.canPerform(.openTheatre))

                Button {
                    store.performAction(.quickLookPreview)
                } label: {
                    Label("Quick Look", systemImage: BHEWorkspaceAction.quickLookPreview.systemImage)
                }
                .disabled(!store.canPerform(.quickLookPreview))
            }
            .buttonStyle(.bordered)

            Divider()

            if entry.kind == .texture {
                Button {
                    store.performAction(.extractSelected)
                } label: {
                    Label("Extract PNG...", systemImage: BHEWorkspaceAction.extractSelected.systemImage)
                }
                .disabled(!(entry.canExtract && store.sourceKind?.isEGame != true))
                .help(extractTextureHelpText)
                .buttonStyle(.borderedProminent)
            }

            if entry.kind == .model || entry.kind == .course || entry.kind == .field || entry.kind == .part {
                Button {
                    store.performAction(.export3DAsset)
                } label: {
                    Label(BHEWorkspaceAction.export3DAsset.label, systemImage: BHEWorkspaceAction.export3DAsset.systemImage)
                }
                .disabled(!store.canPerform(.export3DAsset))
                .help(store.helpText(for: .export3DAsset))
                .buttonStyle(.bordered)
            }

            if entry.kind == .shop {
                Button {
                    store.performAction(.exportShopTextures)
                } label: {
                    Label(BHEWorkspaceAction.exportShopTextures.label, systemImage: BHEWorkspaceAction.exportShopTextures.systemImage)
                }
                .disabled(!store.canPerform(.exportShopTextures))
                .help(store.helpText(for: .exportShopTextures))
                .buttonStyle(.bordered)
            }

            Button {
                store.performAction(.validateReplacement)
            } label: {
                Label("Validate Replacement...", systemImage: BHEWorkspaceAction.validateReplacement.systemImage)
            }
            .disabled(!entry.canReplace)
            .help(store.helpText(for: .validateReplacement))
            .buttonStyle(.bordered)

            Button {
                store.performAction(.createPatchedCopy)
            } label: {
                Label("Create Patched Copy...", systemImage: BHEWorkspaceAction.createPatchedCopy.systemImage)
            }
            .disabled(!entry.canReplace)
            .help(store.helpText(for: .createPatchedCopy))
            .buttonStyle(.bordered)

            Divider()

            HStack {
                Button {
                    store.copySelectedName()
                } label: {
                    Label("Copy Name", systemImage: "doc.on.doc")
                }

                Button {
                    store.copySelectedOffset()
                } label: {
                    Label("Copy Offset", systemImage: "location.viewfinder")
                }
            }
            .buttonStyle(.bordered)
        }
    }

    private var extractTextureHelpText: String {
        if store.sourceKind?.isEGame == true {
            return "Road Trip / HG2 / HG3 texture export is not connected for this row."
        }
        return store.helpText(for: .extractSelected)
    }
}

private struct CapabilityRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Text(label)
                .font(.callout.weight(.medium))
                .foregroundStyle(.secondary)
                .frame(width: 92, alignment: .leading)
            Text(value)
                .font(.callout)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

private struct MetadataGrid: View {
    let entry: BHEEntry

    var body: some View {
        Grid(alignment: .leadingFirstTextBaseline, horizontalSpacing: 22, verticalSpacing: 10) {
            MetadataRow(label: "Service Bay", value: entry.cpkName)
            if entry.serviceBayName != nil {
                MetadataRow(label: "Bay Name", value: entry.serviceBayDisplayName)
            }
            MetadataRow(label: "Format", value: entry.format)
            MetadataRow(label: "Dimensions", value: entry.dimensionsText)
            MetadataRow(label: "Palette", value: entry.paletteText)
            if let meshCount = entry.meshCount {
                MetadataRow(label: "Meshes", value: "\(meshCount)")
            }
            if let textureCount = entry.textureCount {
                MetadataRow(label: "Textures", value: "\(textureCount)")
            }
            MetadataRow(label: "Sector", value: "\(entry.sector)")
            MetadataRow(label: "Offset", value: entry.offsetText)
            MetadataRow(label: "Size", value: entry.sizeText)
            MetadataRow(label: "Identifier", value: entry.id)
        }
        .textSelection(.enabled)
    }
}

private struct MetadataRow: View {
    let label: String
    let value: String

    var body: some View {
        GridRow {
            Text(label)
                .foregroundStyle(.secondary)
            Text(value)
                .monospacedDigit()
        }
        Divider()
            .gridCellColumns(2)
    }
}
