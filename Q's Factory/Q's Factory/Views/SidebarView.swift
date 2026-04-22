import SwiftUI

struct SidebarView: View {
    @Bindable var store: BHEWorkspaceStore

    var body: some View {
        List(selection: $store.selectedGroupID) {
            Section("Garage") {
                if let iso = store.isoSummary {
                    GarageSourceRow(iso: iso, sourceKind: store.sourceKindDisplayName)
                } else {
                    Label("No Garage Source", systemImage: "externaldrive")
                        .foregroundStyle(.secondary)
                }
            }

            if store.hasWorkspace {
                Section("Service Bays") {
                    ForEach(store.groups) { group in
                        HStack(spacing: 10) {
                            Image(systemName: group.systemImage)
                                .foregroundStyle(group.id == "all" ? QFactoryTheme.factoryBlue : .secondary)
                                .frame(width: 16)

                            VStack(alignment: .leading, spacing: 2) {
                                Text(group.title)
                                    .lineLimit(1)
                                Text(group.detail)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(1)
                            }
                        }
                        .tag(group.id)
                    }
                }
            }
        }
        .listStyle(.sidebar)
        .navigationTitle("Garage")
    }
}

private struct GarageSourceRow: View {
    let iso: BHEISOSummary
    let sourceKind: String

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: iso.sourceFamily == "egame" ? "car.side" : "gamecontroller")
                .foregroundStyle(QFactoryTheme.factoryBlue)
                .frame(width: 18)

            VStack(alignment: .leading, spacing: 2) {
                Text(iso.gameTitle)
                    .font(.headline)
                    .lineLimit(2)
                Text("\(iso.variant) - \(sourceKind)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                Text(iso.isoName)
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .lineLimit(1)
            }
        }
        .padding(.vertical, 4)
    }
}
