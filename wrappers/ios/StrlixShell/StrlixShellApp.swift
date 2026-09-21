import SwiftUI
import WebKit

/// Thin native shell around the phone-first Strlix web market/viewer.
struct StrlixWebView: UIViewRepresentable {
    let url: URL

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        configuration.allowsInlineMediaPlayback = true
        configuration.mediaTypesRequiringUserActionForPlayback = []

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.isOpaque = false
        webView.backgroundColor = .black
        webView.load(URLRequest(url: url, cachePolicy: .useProtocolCachePolicy))
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        // Navigation is intentionally owned by the web viewer after first load.
    }

    final class Coordinator: NSObject, WKNavigationDelegate {
        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
        ) {
            // Keep the shell HTTPS-only. External schemes are not a native escape hatch.
            guard let scheme = navigationAction.request.url?.scheme?.lowercased(), scheme == "https" else {
                decisionHandler(.cancel)
                return
            }
            decisionHandler(.allow)
        }
    }
}

@main
struct StrlixShellApp: App {
    private var marketURL: URL {
        let configured = Bundle.main.object(forInfoDictionaryKey: "StrlixWebURL") as? String
            ?? "https://YOUR_HOST/market/"
        return URL(string: configured) ?? URL(string: "https://YOUR_HOST/market/")!
    }

    var body: some Scene {
        WindowGroup {
            StrlixWebView(url: marketURL)
                .ignoresSafeArea()
                .preferredColorScheme(.dark)
        }
    }
}
