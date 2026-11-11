/** Fixed full-screen looping video. `visible` keeps the video vivid (login); default adds a cream/light-blue
 * wash so page text stays readable. */
export function VideoBackdrop({ visible = false }: { visible?: boolean }) {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden bg-[#EAF4FB]" aria-hidden="true">
      <video className="h-full w-full object-cover" src="/loginbackground.mp4" autoPlay muted loop playsInline />
      <div
        className={
          visible
            ? 'absolute inset-0 bg-gradient-to-b from-[#0B2A4A]/25 via-transparent to-[#0B2A4A]/35'
            : 'absolute inset-0 bg-gradient-to-b from-[#FFF8EA]/80 via-[#E3F1FA]/70 to-[#FFF8EA]/85'
        }
      />
    </div>
  )
}
