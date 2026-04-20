import { useState, useEffect } from 'react'
import { listContacts } from '../api/client'

export interface ContactCounts {
  pending: number
  unparsed: number
}

export function useContactCounts(refreshKey: number): ContactCounts {
  const [counts, setCounts] = useState<ContactCounts>({ pending: 0, unparsed: 0 })

  useEffect(() => {
    Promise.all([
      listContacts({ status: 'pending' }),
      listContacts({ status: 'unparsed' }),
    ]).then(([pending, unparsed]) => {
      setCounts({ pending: pending.length, unparsed: unparsed.length })
    })
  }, [refreshKey])

  return counts
}
