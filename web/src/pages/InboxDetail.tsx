interface Props {
  id: string
  onAction: () => void
}

export function InboxDetail({ id }: Props) {
  return <div className="p-6 text-sm text-gray-400">Loading {id}…</div>
}

export default InboxDetail
