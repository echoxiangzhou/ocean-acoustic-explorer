declare module 'react-plotly.js' {
  import { Component } from 'react'
  import { Layout, Config, Data } from 'plotly.js-dist-min'

  interface PlotParams {
    data: Data[]
    layout?: Partial<Layout>
    config?: Partial<Config>
    style?: React.CSSProperties
    className?: string
    onUpdate?: (figure: any) => void
    onClick?: (event: any) => void
  }

  export default class Plot extends Component<PlotParams> {}
}

declare module 'plotly.js-dist-min' {
  export * from 'plotly.js'
}
