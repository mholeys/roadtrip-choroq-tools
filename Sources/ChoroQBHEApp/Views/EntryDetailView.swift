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
                            TexturePreviewView(entry: entry)
                                .frame(maxWidth: .infinity)
                        }

                        MetadataGrid(entry: entry)

                        HStack {
                            Button {
                                store.markActionUnavailable("Extract")
                            } label: {
                                Label("Extract PNG", systemImage: "square.and.arrow.down")
                            }
                            .disabled(!entry.canExtract)

                            Button {
                                store.markActionUnavailable("Replace")
                            } label: {
                                Label("Validate and Replace", systemImage: "arrow.triangle.2.circlepath")
                            }
                            .disabled(!entry.canReplace)

                            Spacer()
                        }
                    }
                    .padding(22)
                    .frame(maxWidth: 620, alignment: .leading)
                }
            } else {
                ContentUnavailableView(
                    "No Selection",
                    systemImage: "sidebar.left",
                    description: Text("Select an entry to inspect its texture data, offsets, and supported actions.")
                )
            }
        }
        .navigationTitle("Inspector")
    }
}

private struct DetailHeader: View {
    let entry: BHEEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(entry.kind.displayName, systemImage: entry.kind.systemImage)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Text(entry.name)
                .font(.title2.weight(.semibold))
                .textSelection(.enabled)

            Label(entry.support.displayName, systemImage: entry.support.systemImage)
                .font(.callout)
                .foregroundStyle(.secondary)
        }
    }
}

private struct MetadataGrid: View {
    let entry: BHEEntry

    var body: some View {
        Grid(alignment: .leadingFirstTextBaseline, horizontalSpacing: 22, verticalSpacing: 10) {
            MetadataRow(label: "Container", value: entry.cpkName)
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
