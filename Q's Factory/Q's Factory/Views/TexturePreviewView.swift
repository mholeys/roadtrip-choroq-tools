import SwiftUI
import AppKit

struct TexturePreviewView: View {
    let entry: BHEEntry
    let background: BHEPreviewBackground
    let previewURL: URL?
    let isLoading: Bool
    let failureMessage: String?

    private var aspectRatio: CGFloat {
        guard let width = entry.width,
              let height = entry.height,
              height > 0 else {
            return 1
        }
        return CGFloat(width) / CGFloat(height)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Inspection Preview", systemImage: "photo")
                .font(.headline)
                .foregroundStyle(.primary)

            ZStack {
                previewBackground

                if let previewImage {
                    Image(nsImage: previewImage)
                        .resizable()
                        .interpolation(.none)
                        .scaledToFit()
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
            .accessibilityLabel("Texture preview for \(entry.name)")
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
            return "Generating preview..."
        }
        if let failureMessage {
            return failureMessage
        }
        switch entry.support {
        case .compressed:
            return "Compressed entry"
        case .supported, .readOnly, .risky, .unknown:
            return "Preview unavailable"
        }
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
