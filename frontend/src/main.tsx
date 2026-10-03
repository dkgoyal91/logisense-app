import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/inter'
import './index.css'
import App from './App.tsx'
import { GameApp } from './game/GameApp.tsx'
import { pickGameRoute } from './game/lib/route.ts'

const gameRole = pickGameRoute(window.location.pathname)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {gameRole ? <GameApp role={gameRole} /> : <App />}
  </StrictMode>,
)
