export default function AlignIcon({ align }: { align: 'left' | 'center' | 'right' }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
      {align === 'left' && (
        <>
          <rect x="1" y="2" width="14" height="1.5" rx="0.5" />
          <rect x="1" y="6" width="10" height="1.5" rx="0.5" />
          <rect x="1" y="10" width="12" height="1.5" rx="0.5" />
          <rect x="1" y="14" width="8" height="1.5" rx="0.5" />
        </>
      )}
      {align === 'center' && (
        <>
          <rect x="1" y="2" width="14" height="1.5" rx="0.5" />
          <rect x="3" y="6" width="10" height="1.5" rx="0.5" />
          <rect x="2" y="10" width="12" height="1.5" rx="0.5" />
          <rect x="4" y="14" width="8" height="1.5" rx="0.5" />
        </>
      )}
      {align === 'right' && (
        <>
          <rect x="1" y="2" width="14" height="1.5" rx="0.5" />
          <rect x="5" y="6" width="10" height="1.5" rx="0.5" />
          <rect x="3" y="10" width="12" height="1.5" rx="0.5" />
          <rect x="7" y="14" width="8" height="1.5" rx="0.5" />
        </>
      )}
    </svg>
  );
}
