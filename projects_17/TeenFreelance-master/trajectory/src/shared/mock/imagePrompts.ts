/**
 * Image-prompt placeholder registry — ported 1:1 from the concept prototype
 * (../задача.md, Data.imagePrompts). Single source of truth for IMG-01..07;
 * see ../TRAJECTORY_ROADMAP.md §2.3 for the prompt formula.
 */
import type { ImagePromptDef } from '../../types';

export const imagePrompts: Record<string, ImagePromptDef> = {
  'IMG-01': {
    id: 'IMG-01',
    label: 'HERO · Cinematic wide 21:9',
    aspect: '21:9',
    prompt:
      'Cinematic wide shot, teenagers working at a shared studio table with laptops and drafting tools, warm paper tones #F4F2EE and ink black, burnt sienna accent light, editorial photography style, swiss composition, natural window light, grayscale background atmosphere, no text, no watermark, 21:9',
  },
  'IMG-02': {
    id: 'IMG-02',
    label: 'AVATAR · 1:1',
    aspect: '1:1',
    prompt:
      'Minimal editorial portrait of a 17-year-old designer, neutral warm background, confident calm expression, soft daylight, muted palette with burnt sienna accent, square crop 1:1, no text',
  },
  'IMG-03': {
    id: 'IMG-03',
    label: 'TASK COVER · 16:9',
    aspect: '16:9',
    prompt:
      'Brand identity workspace flatlay: logo sketches, typography specimen sheets, warm coffee-house color palette drafts, swiss grid layout, top-down cinematic photography, paper texture, no readable text, 16:9',
  },
  'IMG-04': {
    id: 'IMG-04',
    label: 'WORKSPACE · 4:3',
    aspect: '4:3',
    prompt:
      'Clean minimal upload dropzone background: abstract paper texture with subtle swiss grid lines and a burnt sienna corner mark, generous negative space, editorial print aesthetic, no text, 4:3',
  },
  'IMG-05': {
    id: 'IMG-05',
    label: 'PORTFOLIO · EcoFarm · 16:9',
    aspect: '16:9',
    prompt:
      'Modern eco-farm landing page hero visual: greenhouse with young plants, warm morning light, editorial minimalism, muted green and paper tones, no text, 16:9',
  },
  'IMG-06': {
    id: 'IMG-06',
    label: 'PORTFOLIO · Neon Poster · 4:3',
    aspect: '4:3',
    prompt:
      'Poster design mockup on concrete wall: abstract neon geometric shapes, dark background, single burnt sienna accent, swiss typography layout without readable text, cinematic lighting, 4:3',
  },
  'IMG-07': {
    id: 'IMG-07',
    label: 'PORTFOLIO · Tech Blog · 16:9',
    aspect: '16:9',
    prompt:
      'Editorial article illustration: minimal 3D paper abstract shape composition on warm paper background, subtle shadows, ink black and burnt sienna palette, no text, 16:9',
  },
};

export const getImagePrompt = (id: string): ImagePromptDef | undefined => imagePrompts[id];
