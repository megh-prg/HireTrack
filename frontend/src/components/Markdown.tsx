import type { ReactNode } from 'react'

/** Tiny renderer for the prep answers: fenced code, bullet/numbered lists, **bold**, `code`. */
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={i}>{part.slice(2, -2)}</strong>
    if (part.startsWith('`') && part.endsWith('`')) return <code key={i}>{part.slice(1, -1)}</code>
    return part
  })
}

export default function Markdown({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  const lines = text.split('\n')
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (line.startsWith('```')) {
      const code: string[] = []
      i++
      while (i < lines.length && !lines[i].startsWith('```')) code.push(lines[i++])
      i++
      blocks.push(
        <pre key={blocks.length}>
          <code>{code.join('\n')}</code>
        </pre>,
      )
    } else if (/^\s*(-|\d+\.)\s/.test(line)) {
      const ordered = /^\s*\d+\./.test(line)
      const items: string[] = []
      while (i < lines.length && /^\s*(-|\d+\.)\s/.test(lines[i])) items.push(lines[i++].replace(/^\s*(-|\d+\.)\s/, ''))
      const children = items.map((item, k) => <li key={k}>{inline(item)}</li>)
      blocks.push(ordered ? <ol key={blocks.length}>{children}</ol> : <ul key={blocks.length}>{children}</ul>)
    } else if (line.trim()) {
      const para: string[] = []
      while (i < lines.length && lines[i].trim() && !lines[i].startsWith('```') && !/^\s*(-|\d+\.)\s/.test(lines[i])) para.push(lines[i++])
      blocks.push(<p key={blocks.length}>{inline(para.join(' '))}</p>)
    } else {
      i++
    }
  }
  return <div className="answer">{blocks}</div>
}
