import type { SVGProps } from "react";

/**
 * SVG path string for the custom FlightWise airplane structure matching the uploaded flight PNG.
 * Centered at (0,0) facing right (+X / 0 degrees) so SVG `<animateMotion rotate="auto">`
 * aligns the aircraft along the flight path tangent seamlessly.
 */
export const FLIGHT_ICON_PATH =
  "M 14 0 C 14 -1.6 12.5 -3.2 9.8 -4.2 L 2.2 -5.2 L -2.4 -14 C -3.2 -15.2 -4.6 -15.6 -5.6 -14.8 C -6.4 -14 -6.6 -12.6 -5.8 -11.5 L -2.6 -4.8 L -9 -4.5 L -11.6 -9 C -12.3 -9.8 -13.5 -10 -14.3 -9.3 C -14.9 -8.6 -15 -7.5 -14.4 -6.7 L -12.8 -2.8 C -13.6 -1.6 -14 0 -14 0 C -14 0 -13.6 1.6 -12.8 2.8 L -14.4 6.7 C -15 7.5 -14.9 8.6 -14.3 9.3 C -13.5 10 -12.3 9.8 -11.6 9 L -9 4.5 L -2.6 4.8 L -5.8 11.5 C -6.6 12.6 -6.4 14 -5.6 14.8 C -4.6 15.6 -3.2 15.2 -2.4 14 L 2.2 5.2 L 9.8 4.2 C 12.5 3.2 14 1.6 14 0 Z";

/** Scaled path (0.6x) optimized for SVG map route animations */
export const FLIGHT_MAP_ICON_PATH =
  "M 8.4 0 C 8.4 -1 7.5 -1.9 5.9 -2.5 L 1.3 -3.1 L -1.4 -8.4 C -1.9 -9.1 -2.8 -9.4 -3.4 -8.9 C -3.8 -8.4 -4 -7.6 -3.5 -6.9 L -1.6 -2.9 L -5.4 -2.7 L -7 -5.4 C -7.4 -5.9 -8.1 -6 -8.6 -5.6 C -8.9 -5.2 -9 -4.5 -8.6 -4 L -7.7 -1.7 C -8.2 -1 -8.4 0 -8.4 0 C -8.4 0 -8.2 1 -7.7 1.7 L -8.6 4 C -9 4.5 -8.9 5.2 -8.6 5.6 C -8.1 6 -7.4 5.9 -7 5.4 L -5.4 2.7 L -1.6 2.9 L -3.5 6.9 C -4 7.6 -3.8 8.4 -3.4 8.9 C -2.8 9.4 -1.9 9.1 -1.4 8.4 L 1.3 3.1 L 5.9 2.5 C 7.5 1.9 8.4 1 8.4 0 Z";

export function FlightIcon({
  className = "h-5 w-5",
  fill = "currentColor",
  ...props
}: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="-16 -16 32 32" className={className} fill={fill} aria-hidden="true" {...props}>
      <path d={FLIGHT_ICON_PATH} />
    </svg>
  );
}
