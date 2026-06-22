import "@react-three/fiber";
import { Object3DNode } from "@react-three/fiber";
import { Line as ThreeLine } from "three";

declare module "@react-three/fiber" {
  interface ThreeElements {
    line: Object3DNode<ThreeLine, typeof ThreeLine>;
    lineSegments: Object3DNode<ThreeLine, typeof ThreeLine>;
  }
}
