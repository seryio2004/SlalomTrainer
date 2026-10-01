import { createRoot } from 'react-dom/client'
import { App } from './App'
import './style.css'

const root = document.getElementById('root')

if (!root) {
  throw new Error('No se encontró el contenedor de la aplicación')
}

createRoot(root).render(<App />)

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  void navigator.serviceWorker.register('/sw.js').catch(() => {})
}
