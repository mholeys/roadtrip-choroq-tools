import SwiftUI

enum QFactoryTheme {
    static let factoryBlue = Color(red: 0.02, green: 0.38, blue: 0.76)
    static let factoryRed = Color(red: 0.82, green: 0.12, blue: 0.15)
    static let hazardYellow = Color(red: 0.96, green: 0.73, blue: 0.10)
    static let serviceGreen = Color(red: 0.20, green: 0.60, blue: 0.36)
    static let toolSteel = Color(red: 0.43, green: 0.48, blue: 0.54)
    static let rubberBlack = Color(red: 0.09, green: 0.10, blue: 0.12)

    static var panelFill: Color {
        Color(nsColor: .controlBackgroundColor).opacity(0.82)
    }

    static var panelStroke: Color {
        Color(nsColor: .separatorColor).opacity(0.70)
    }

    static var workbenchTint: Color {
        Color(nsColor: .textBackgroundColor)
    }

    static func supportTint(for support: BHESupportState) -> Color {
        switch support {
        case .supported:
            serviceGreen
        case .exportable:
            serviceGreen
        case .scanOnly:
            factoryBlue
        case .unsupported:
            .secondary
        case .readOnly:
            factoryBlue
        case .compressed:
            .secondary
        case .risky:
            hazardYellow
        case .unknown:
            .secondary
        }
    }

    static func kindTint(for kind: BHEEntryKind) -> Color {
        switch kind {
        case .texture, .apt:
            factoryBlue
        case .model, .part, .course, .field:
            factoryRed
        case .shop:
            serviceGreen
        case .graphics:
            factoryBlue
        case .sound:
            toolSteel
        case .lzs:
            hazardYellow
        case .text, .cpk:
            toolSteel
        case .unknown:
            .secondary
        }
    }
}

struct WorkshopSection<Content: View>: View {
    let title: String
    let systemImage: String
    @ViewBuilder var content: Content

    var body: some View {
        GroupBox {
            content
                .frame(maxWidth: .infinity, alignment: .leading)
        } label: {
            Label(title, systemImage: systemImage)
                .font(.headline)
                .foregroundStyle(QFactoryTheme.factoryBlue)
        }
        .groupBoxStyle(.automatic)
    }
}
