import SwiftUI

struct TexturePreviewView: View {
    let entry: BHEEntry

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
            Text("Preview")
                .font(.headline)

            ZStack {
                Checkerboard()
                Rectangle()
                    .fill(previewGradient)
                    .opacity(entry.support == .compressed ? 0.2 : 0.72)
                    .padding(18)
                Image(systemName: entry.support == .compressed ? "archivebox" : "photo")
                    .font(.system(size: 42, weight: .regular))
                    .foregroundStyle(.secondary)
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

    private var previewGradient: LinearGradient {
        LinearGradient(
            colors: [.blue.opacity(0.55), .green.opacity(0.35), .orange.opacity(0.45)],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
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
