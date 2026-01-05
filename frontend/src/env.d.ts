/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface Window {
  $message?: {
    success(message: string): void
    error(message: string): void
    warning(message: string): void
    info(message: string): void
  }
}