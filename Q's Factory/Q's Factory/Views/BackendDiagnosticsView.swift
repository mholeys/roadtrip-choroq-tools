import SwiftUI

struct BackendDiagnosticsView: View {
    @Bindable var store: BHEWorkspaceStore

    var body: some View {
        VStack(spacing: 0) {
            header

            Divider()

            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    runtimeSection
                    dependencySection
                    helperSection
                    capabilitySection
                }
                .padding(20)
            }

            Divider()

            HStack {
                Button {
                    Task { await store.refreshBackendDiagnostics() }
                } label: {
                    Label("Refresh", systemImage: "arrow.clockwise")
                }
                .disabled(store.isBackendDiagnosticsLoading)

                Spacer()

                Button("Done") {
                    store.isBackendDiagnosticsPresented = false
                }
                .keyboardShortcut(.defaultAction)
            }
            .padding(16)
        }
        .frame(width: 620)
        .frame(minHeight: 520)
        .task {
            if store.backendHealth == nil && !store.isBackendDiagnosticsLoading {
                await store.refreshBackendDiagnostics()
            }
        }
    }

    private var header: some View {
        HStack(spacing: 12) {
            Image(systemName: "stethoscope")
                .font(.system(size: 28))
                .foregroundStyle(QFactoryTheme.factoryBlue)

            VStack(alignment: .leading, spacing: 3) {
                Text("Backend Diagnostics")
                    .font(.title2.weight(.semibold))
                Text("Checks the signed app bundle backend, Python runtime, parser modules, and optional helper tools.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer()

            if store.isBackendDiagnosticsLoading {
                ProgressView()
                    .controlSize(.small)
            }
        }
        .padding(20)
    }

    @ViewBuilder
    private var runtimeSection: some View {
        DiagnosticsSection(title: "Runtime", systemImage: "terminal") {
            if let version = store.backendVersion, let health = store.backendHealth {
                DiagnosticsRow(label: "Protocol", value: "\(version.protocolVersion)")
                DiagnosticsRow(label: "Backend", value: version.backendVersion)
                DiagnosticsRow(label: "Mode", value: version.readOnly ? "Read-only source access" : "Write-capable")
                DiagnosticsRow(label: "Python", value: health.pythonVersion)
                DiagnosticsRow(label: "Executable", value: health.pythonExecutable)
            } else {
                Text("Run diagnostics to inspect the backend bundled with this build.")
                    .foregroundStyle(.secondary)
            }
        }
    }

    @ViewBuilder
    private var dependencySection: some View {
        DiagnosticsSection(title: "Python Modules", systemImage: "shippingbox") {
            if let dependencies = store.backendHealth?.dependencies {
                ForEach(dependencies) { dependency in
                    HStack {
                        Label(
                            dependency.name,
                            systemImage: dependency.available ? "checkmark.circle" : "xmark.circle"
                        )
                        .foregroundStyle(dependency.available ? QFactoryTheme.serviceGreen : QFactoryTheme.hazardYellow)

                        Text(dependency.module)
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        Spacer()

                        Text(dependency.requiredForBHE ? "BHE required" : "Optional path")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            } else {
                Text("No dependency status has been loaded yet.")
                    .foregroundStyle(.secondary)
            }
        }
    }

    @ViewBuilder
    private var helperSection: some View {
        DiagnosticsSection(title: "Helper Tools", systemImage: "externaldrive.badge.gearshape") {
            if let bchunk = store.backendHealth?.bchunk {
                DiagnosticsRow(
                    label: "bchunk",
                    value: bchunk.available ? (bchunk.path ?? "Available on PATH") : "Not found"
                )
                Text("BIN/CUE conversion remains an optional helper flow. Q's Factory does not modify the original BIN or CUE files.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
            } else {
                Text("No helper tool status has been loaded yet.")
                    .foregroundStyle(.secondary)
            }
        }
    }

    @ViewBuilder
    private var capabilitySection: some View {
        DiagnosticsSection(title: "Capabilities", systemImage: "checklist") {
            if let supportedTypes = store.supportedTypes {
                ForEach(supportedTypes.sourceTypes, id: \.extension) { sourceType in
                    VStack(alignment: .leading, spacing: 2) {
                        HStack {
                            Text(sourceType.extension.uppercased())
                                .font(.headline)
                            Text(sourceType.support)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Spacer()
                            Text(sourceType.role)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Text(sourceType.notes)
                            .font(.callout)
                            .foregroundStyle(.secondary)
                    }
                }

                Divider()

                DiagnosticsRow(label: "Original ISO writes", value: supportedTypes.writeSupport.originalISOModification ? "Available" : "Not implemented")
                DiagnosticsRow(label: "Patched copy writes", value: supportedTypes.writeSupport.patchedCopyWriting ? "Available" : "Not implemented")
                DiagnosticsRow(label: "Replacement validation", value: supportedTypes.writeSupport.replacementValidation ? "Available" : "Not implemented")
            } else {
                Text("No capability data has been loaded yet.")
                    .foregroundStyle(.secondary)
            }
        }
    }
}

private struct DiagnosticsSection<Content: View>: View {
    let title: String
    let systemImage: String
    @ViewBuilder var content: Content

    var body: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 10) {
                content
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        } label: {
            Label(title, systemImage: systemImage)
                .font(.headline)
        }
    }
}

private struct DiagnosticsRow: View {
    let label: String
    let value: String

    var body: some View {
        Grid(alignment: .leadingFirstTextBaseline, horizontalSpacing: 16, verticalSpacing: 8) {
            GridRow {
                Text(label)
                    .foregroundStyle(.secondary)
                Text(value)
                    .textSelection(.enabled)
            }
        }
    }
}
