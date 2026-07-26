declare module 'svg-pan-zoom' {
  export interface SvgPanZoomInstance {
    zoomIn(): void;
    zoomOut(): void;
    resetZoom(): void;
    center(): void;
    fit(): void;
    resize(): void;
    destroy(): void;
  }

  export interface SvgPanZoomOptions {
    controlIconsEnabled?: boolean
    fit?: boolean
    center?: boolean
    minZoom?: number
    maxZoom?: number
    zoomScaleSensitivity?: number
    dblClickZoomEnabled?: boolean
  }

  export default function svgPanZoom(
      element: SVGElement,
      options?: SvgPanZoomOptions,
      ): SvgPanZoomInstance;
}