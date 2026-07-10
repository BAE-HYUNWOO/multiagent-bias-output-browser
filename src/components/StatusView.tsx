export function LoadingView({ message = '데이터를 불러오는 중입니다.' }: { message?: string }) {
  return (
    <div className="status-panel">
      <div className="spinner" />
      <p>{message}</p>
    </div>
  )
}

export function ErrorView({ message }: { message: string }) {
  return (
    <div className="status-panel error-panel">
      <strong>데이터를 불러오지 못했습니다.</strong>
      <p>{message}</p>
    </div>
  )
}

export function EmptyView() {
  return (
    <div className="empty-state">
      <div className="empty-folder">📂</div>
      <h2>아직 UI 데이터가 생성되지 않았습니다.</h2>
      <p>
        <code>source_data/outputs/split001</code>에 결과를 복사하고,
        <code> scripts/rebuild_data.ps1</code>을 실행하세요.
      </p>
    </div>
  )
}
