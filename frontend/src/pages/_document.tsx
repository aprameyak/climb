import { Html, Head, Main, NextScript } from 'next/document';

export default function Document() {
  return (
    <Html lang="en" className="dark">
      <Head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <meta name="color-scheme" content="dark" />
        <meta name="robots" content="noindex" />
      </Head>
      <body className="bg-slate-950 text-slate-100 antialiased">
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
