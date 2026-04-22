import SwiftUI

struct EntryDetailView: View {
    @Bindable var store: BHEWorkspaceStore

    var body: some View {
        Group {
            if let entry = store.selectedEntry {
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        DetailHeader(entry: entry)

                        if entry.kind == .texture {
                            TexturePreviewView(
                                entry: entry,
                                background: store.previewBackground,
                                previewURL: store.previewEntryID == entry.id ? store.previewImageURL : nil,
                                isLoading: store.previewEntryID == entry.id && store.isPreviewLoading,
                                failureMessage: store.previewEntryID == entry.id ? store.previewFailureMessage : nil
                            )
                                .frame(maxWidth: .infinity)
                        } else {
                            ReadOnlyInspectionView(entry: entry)
                        }

                        AssetCapabilityView(entry: entry, sourceKind: store.sourceKind)

                        WorkshopSection(title: "Part Specs", systemImage: "list.bullet.rectangle") {
                            MetadataGrid(entry: entry)
                        }

                        WorkshopSection(title: "Service Actions", systemImage: "wrench.adjustable") {
                            ContextualActionsView(store: store, entry: entry)
                        }
                        .controlSize(.regular)
                    }
                    .padding(22)
                    .frame(maxWidth: 620, alignment: .leading)
                }
                .task(id: entry.id) {
                    await store.loadPreview(for: entry)
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

private struct DetailHeader: View {
    let entry: BHEEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(entry.kind.displayName, systemImage: entry.kind.systemImage)
                .font(.subheadline)
                .foregroundStyle(QFactoryTheme.factoryBlue)

            Text(entry.name)
                .font(.title2.weight(.semibold))
                .textSelection(.enabled)

            Label(entry.support.displayName, systemImage: entry.support.systemImage)
                .font(.callout)
                .foregroundStyle(QFactoryTheme.supportTint(for: entry.support))
        }
    }
}

private struct ReadOnlyInspectionView: View {
    let entry: BHEEntry

    var body: some View {
        WorkshopSection(title: "Inspection Preview", systemImage: entry.kind.systemImage) {
            VStack(spacing: 10) {
                Image(systemName: entry.kind.systemImage)
                    .font(.system(size: 36, weight: .regular))
                    .foregroundStyle(QFactoryTheme.factoryBlue)
                Text(entry.support == .readOnly ? "Scan-only part" : entry.support.displayName)
                    .font(.headline)
                Text("Q's Factory can list this part and inspect its metadata. Preview and extraction will stay disabled until the backend exposes a safe reader for this format.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 20)
        }
        .accessibilityElement(children: .combine)
    }
}

private struct AssetCapabilityView: View {
    let entry: BHEEntry
    let sourceKind: BHESourceKind?

    var body: some View {
        WorkshopSection(title: "Asset Role", systemImage: "info.circle") {
            VStack(alignment: .leading, spacing: 10) {
                CapabilityRow(label: "Contains", value: containsText)
                CapabilityRow(label: "Displays", value: displaysText)
                CapabilityRow(label: "macOS Native", value: nativeDisplayText)
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
            return "Shop or game-data record from the source layout."
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
            return "Scan-only in this build. Native 3D display needs conversion to a SceneKit, Model I/O, OBJ, or USDZ representation."
        case .apt, .cpk:
            return "Container metadata. Select a child texture row for image preview."
        case .lzs:
            return "Compressed metadata only."
        case .text, .shop, .unknown:
            return "Metadata only."
        }
    }

    private var nativeDisplayText: String {
        switch entry.kind {
        case .texture:
            return "Yes after backend decoding: SwiftUI displays the generated PNG with NSImage."
        case .model, .course, .field, .part:
            return "Not raw. macOS can display OBJ, USDZ, SceneKit scenes, or Model I/O meshes after conversion."
        case .apt, .cpk, .lzs, .text, .shop, .unknown:
            return "Not directly. These are custom game/archive formats and need backend parsing first."
        }
    }
}

private struct ContextualActionsView: View {
    let store: BHEWorkspaceStore
    let entry: BHEEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            if entry.kind == .texture {
                Button {
                    store.performAction(.extractSelected)
                } label: {
                    Label("Extract PNG...", systemImage: BHEWorkspaceAction.extractSelected.systemImage)
                }
                .disabled(!entry.canExtract)
                .help(store.helpText(for: .extractSelected))
                .buttonStyle(.borderedProminent)
            }

            if entry.kind == .model || entry.kind == .course || entry.kind == .field || entry.kind == .part {
                Button {
                    store.performAction(.extractSelected)
                } label: {
                    Label("Export 3D Asset...", systemImage: "cube.transparent")
                }
                .disabled(true)
                .help("3D export needs a backend converter to OBJ or USDZ before macOS can preview it natively.")
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
            MetadataRow(label: "Format", value: entry.format)
            MetadataRow(label: "Dimensions", value: entry.dimensionsText)
            MetadataRow(label: "Palette", value: entry.paletteText)
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
