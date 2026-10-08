import { ConfirmButton } from '../shared/ConfirmButton.tsx'

export function RaceButton({ onDone }: { onDone: () => void }) {
  return (
    <ConfirmButton className="race-button" onConfirm={onDone}>
      🏁 Built it? I'm done!
    </ConfirmButton>
  )
}
