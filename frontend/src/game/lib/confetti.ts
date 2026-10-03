import confetti from 'canvas-confetti'

export const fireConfetti = (): void => {
  void confetti({ particleCount: 160, spread: 90, origin: { y: 0.6 } })
}
