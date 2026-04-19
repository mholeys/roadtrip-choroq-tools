import SwiftUI

struct SidebarView: View {
    @Bindable var store: BHEWorkspaceStore

    var body: some View {
        List(selection: $store.selectedGroupID) {
            if let iso = store.isoSummary {
                Section("Game") {
                    VStack(alignment: .leading, spacing: 3) {
                        Label(iso.gameTitle, systemImage: "gamecontroller")
                            .font(.headline)
                        Text("\(iso.variant) - \(iso.isoName)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }
                    .padding(.vertical, 4)
                }
            }

            Section("Containers") {
                ForEach(store.groups) { group in
                    HStack(spacing: 10) {
                        Image(systemName: group.systemImage)
                            .foregroundStyle(.secondary)
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
        .listStyle(.sidebar)
        .navigationTitle("BHE")
    }
}
