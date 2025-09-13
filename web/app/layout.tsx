import '../styles/globals.css'

export const metadata = {
  title: 'Nexora News - AI-Powered News Aggregator',
  description: 'Real-time news aggregation with AI enrichment',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}