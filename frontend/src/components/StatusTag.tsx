export default function StatusTag({ enabled }: { enabled: boolean }) {
  return <span className={`tag ${enabled ? 'tag-green' : 'tag-gray'}`}>{enabled ? '● 启用' : '○ 禁用'}</span>
}
