import SwiftUI
import AppKit

struct RasterPreviewView: View {
    let entry: BHEEntry
    let background: BHEPreviewBackground
    let previewURL: URL?
    let previewState: AssetPreviewState
    let isLoading: Bool
    let failureMessage: String?
    @State private var zoom: CGFloat = 1
    @State private var pixelPerfect = true

    private var aspectRatio: CGFloat {
        guard let width = entry.width,
              let height = entry.height,
              height > 0 else {
            if let previewImage, previewImage.size.height > 0 {
                return previewImage.size.width / previewImage.size.height
            }
            return 1
        }
        return CGFloat(width) / CGFloat(height)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(previewTitle, systemImage: "photo")
                .font(.headline)
                .foregroundStyle(.primary)

            ZStack {
                previewBackground

                if let previewImage {
                    Image(nsImage: previewImage)
                        .resizable()
                        .interpolation(pixelPerfect ? .none : .medium)
                        .scaledToFit()
                        .scaleEffect(zoom)
                        .padding(10)
                } else {
                    VStack(spacing: 10) {
                        if isLoading {
                            ProgressView()
                                .controlSize(.small)
                        } else {
                            Image(systemName: entry.support == .compressed ? "archivebox" : "photo")
                                .font(.system(size: 34, weight: .regular))
                                .foregroundStyle(QFactoryTheme.supportTint(for: entry.support))
                        }

                        Text(previewMessage)
                            .font(.callout)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                    }
                    .padding()
                    .background(Color(nsColor: .controlBackgroundColor).opacity(0.86), in: .rect(cornerRadius: 8))
                }
            }
            .aspectRatio(aspectRatio, contentMode: .fit)
            .frame(minHeight: 180, maxHeight: 320)
            .clipShape(.rect(cornerRadius: 8))
            .overlay {
                RoundedRectangle(cornerRadius: 8)
                    .stroke(.separator, lineWidth: 1)
            }
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("\(previewTitle) for \(entry.name)")

            HStack {
                Button {
                    zoom = max(0.5, zoom - 0.25)
                } label: {
                    Image(systemName: "minus.magnifyingglass")
                }
                Button {
                    zoom = min(4, zoom + 0.25)
                } label: {
                    Image(systemName: "plus.magnifyingglass")
                }
                Button {
                    zoom = 1
                } label: {
                    Image(systemName: "arrow.up.left.and.down.right.magnifyingglass")
                }
                Toggle(isOn: $pixelPerfect) {
                    Label("Pixel", systemImage: "square.grid.3x3")
                }
                .toggleStyle(.button)
                Spacer()
                Text(metadataText)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.borderless)
        }
    }

    private var previewTitle: String {
        switch entry.kind {
        case .texture:
            "Texture Preview"
        case .graphics, .shop:
            "Raster Preview"
        default:
            "Generated Preview"
        }
    }

    private var previewImage: NSImage? {
        guard let previewURL else {
            return nil
        }
        return NSImage(contentsOf: previewURL)
    }

    @ViewBuilder
    private var previewBackground: some View {
        switch background {
        case .checkerboard:
            Checkerboard()
        case .black:
            Color.black
        case .white:
            Color.white
        }
    }

    private var previewMessage: String {
        if isLoading {
            return previewState.message ?? "Decoding graphics..."
        }
        if let failureMessage {
            return failureMessage
        }
        switch entry.support {
        case .compressed:
            return "Compressed entry"
        case .supported, .exportable, .scanOnly, .unsupported, .readOnly, .risky, .unknown:
            return entry.kind == .texture ? "Texture preview unavailable" : "Generated preview unavailable"
        }
    }

    private var metadataText: String {
        if let previewImage {
            return "\(Int(previewImage.size.width)) x \(Int(previewImage.size.height))"
        }
        return entry.dimensionsText
    }
}

struct TexturePreviewView: View {
    let entry: BHEEntry
    let background: BHEPreviewBackground
    let previewURL: URL?
    let isLoading: Bool
    let failureMessage: String?

    var body: some View {
        RasterPreviewView(
            entry: entry,
            background: background,
            previewURL: previewURL,
            previewState: isLoading ? .preparing(stage: "Decoding graphics...") : (failureMessage == nil ? .ready : .failed(message: failureMessage ?? "")),
            isLoading: isLoading,
            failureMessage: failureMessage
        )
    }
}

private struct Checkerboard: View {
    private let squareSize: CGFloat = 12

    var body: some View {
        Canvas { context, size in
            let columns = Int(ceil(size.width / squareSize))
            let rows = Int(ceil(size.height / squareSize))

            for row in 0..<rows {
                for column in 0..<columns {
                    let isDark = (row + column).isMultiple(of: 2)
                    let rect = CGRect(
                        x: CGFloat(column) * squareSize,
                        y: CGFloat(row) * squareSize,
                        width: squareSize,
                        height: squareSize
                    )
                    context.fill(
                        Path(rect),
                        with: .color(isDark ? Color(nsColor: .gridColor).opacity(0.35) : Color(nsColor: .textBackgroundColor))
                    )
                }
            }
        }
    }
}
