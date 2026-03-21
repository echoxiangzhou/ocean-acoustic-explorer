import './SectionAnalysis.css'

export function SectionAnalysis() {
  return (
    <div className="module-placeholder">
      <h2>C 区域精细声场分析</h2>
      <p>在地图上画线定义断面 → 设置参数 → 运行声学计算 → 查看传播损失图</p>
      <div className="placeholder-features">
        <div>传播损失 TL(r,z) 伪彩色图</div>
        <div>声线追踪图</div>
        <div>断面声速场</div>
        <div>定深/定距 TL 曲线</div>
      </div>
    </div>
  )
}
