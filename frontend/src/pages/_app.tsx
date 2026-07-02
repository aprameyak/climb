import type { AppProps } from 'next/app';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import Head from 'next/head';
import '../styles/globals.css';

export default function App({ Component, pageProps }: AppProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <>
      <Head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#0f172a" />
        <title>Climb.AI — AI Bouldering Beta Solver</title>
        <meta
          name="description"
          content="AI-powered bouldering beta solver with computer vision and biomechanics"
        />
      </Head>
      <QueryClientProvider client={queryClient}>
        <div className="dark">
          <Component {...pageProps} />
        </div>
      </QueryClientProvider>
    </>
  );
}
