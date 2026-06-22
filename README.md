<div align="center">

<img src="./frontend/public/logo.png" alt="NeoFace Logo" width="120" />

# NeoFace

### Enterprise-Grade Biometric Identity & Payment Infrastructure

**The world's most advanced multi-modal biometric authentication platform.**  
Face · Iris · Fingerprint · Liveness · Deepfake Detection · Continuous Auth · Trust Engine

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7.2-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-Proprietary-red)](https://neoface.io)

---

[Overview](#-overview) · [Architecture](#-architecture) · [Features](#-features) · [Tech Stack](#-tech-stack) · [API Reference](#-api-reference) · [Quick Start](#-quick-start) · [Deployment](#-deployment)

</div>

---

## 🧠 Overview

NeoFace is a **production-ready, enterprise-grade biometric identity and payment platform** built for the post-password era. It combines cutting-edge computer vision, machine learning, and fraud prevention into a single unified infrastructure.

The system is designed to serve as the authentication backbone for:
- **Biometric payment authorization** (Face Pay, Iris Pay, Fingerprint Pay)
- **Identity verification** for KYC/AML compliance
- **Continuous authentication** for high-security enterprise sessions
- **Fraud prevention** with real-time deepfake and spoof detection
- **Multi-tenant B2B SaaS** deployments

> NeoFace processes biometric identity in **<150ms** and supports **1,000+ concurrent users** out of the box.

---

## 🏗 Architecture

```
neoface/
│
├── frontend/                          # Next.js 16 + React 19 (TypeScript)
│   ├── app/                           # App Router pages
│   │   ├── page.tsx                   # Landing page (3D animated hero)
│   │   ├── login/                     # JWT + Firebase OAuth login
│   │   ├── register/                  # User registration
│   │   ├── enroll/                    # Biometric enrollment wizard
│   │   ├── verify/                    # Face verification flow
│   │   ├── checkout-demo/             # Live biometric payment demo
│   │   └── dashboard/                 # Admin control center
│   │       ├── page.tsx               # Stats overview
│   │       ├── analytics/             # Charts & time-series
│   │       ├── users/                 # User management
│   │       ├── logs/                  # Auth & verification audit logs
│   │       ├── bank-accounts/         # Linked payment methods
│   │       ├── fingerprint/           # WebAuthn device management
│   │       ├── identity/              # Identity verification panel
│   │       └── settings/              # System configuration
│   ├── components/
│   │   ├── core/                      # FirebaseAuthProvider, SmoothScroll, NoiseOverlay
│   │   ├── landing/                   # HeroSection, ArchitectureSection, etc.
│   │   ├── layout/                    # Navbar, Footer
│   │   ├── ui/                        # Button, Card, Badge, Input (Radix + CVA)
│   │   └── visuals/                   # 3D BiometricOrbit, FaceMeshCanvas, IdentityCore
│   ├── lib/
│   │   ├── api.ts                     # Axios client (JWT interceptors)
│   │   ├── firebase.ts                # Firebase SDK initialization
│   │   └── firebase-auth.ts           # Google OAuth helpers
│   ├── store/
│   │   ├── auth.ts                    # Zustand auth state (JWT, user profile)
│   │   ├── enrollment.ts              # Enrollment flow state
│   │   └── verification.ts            # Verification result state
│   ├── types/
│   │   └── index.ts                   # Shared TypeScript types
│   └── eslint.config.mjs              # ESLint v9 flat config             ★ NEW
│
└── backend/                           # FastAPI + Python 3.12
    ├── app/
    │   ├── api/v1/                    # REST API endpoints (18 modules)
    │   │   ├── auth.py                # Login, register, refresh, Google OAuth
    │   │   ├── enrollment.py          # Multi-image face enrollment
    │   │   ├── verification.py        # 1:N face verification
    │   │   ├── biometrics.py          # Iris & fingerprint enrollment/verify
    │   │   ├── payments.py            # Biometric payment authorization
    │   │   ├── webauthn.py            # FIDO2/WebAuthn device fingerprint
    │   │   ├── merchants.py           # Merchant management
    │   │   ├── bank_accounts.py       # Payment method linking
    │   │   ├── users.py               # User CRUD (admin)
    │   │   ├── dashboard.py           # Analytics & reporting
    │   │   ├── liveness.py            # Passive + active liveness APIs  ★ NEW
    │   │   ├── emotion.py             # Emotion recognition API           ★ NEW
    │   │   ├── headpose.py            # Head pose estimation API          ★ NEW
    │   │   ├── deepfake.py            # Deepfake detection API            ★ NEW
    │   │   ├── risk.py                # Trust Score Engine API            ★ NEW
    │   │   ├── device_trust.py        # Device integrity API              ★ NEW
    │   │   ├── behavioral.py          # Behavioral biometrics API         ★ NEW
    │   │   └── continuous_auth.py     # Continuous authentication API     ★ NEW
    │   ├── core/
    │   │   ├── config.py              # Pydantic Settings (50+ env vars)
    │   │   ├── database.py            # Async SQLAlchemy engine (Supabase)
    │   │   ├── security.py            # JWT + bcrypt + OAuth2
    │   │   └── logging.py             # Loguru structured logging
    │   ├── models/                    # SQLAlchemy ORM models (22 tables)
    │   │   ├── user.py                # User identity model
    │   │   ├── face_embedding.py      # ArcFace 512-d embeddings
    │   │   ├── iris_embedding.py      # Gabor IrisCode (256B)
    │   │   ├── fingerprint_template.py # ISO/IEC 19794-2 templates
    │   │   ├── transaction.py         # Payment transactions
    │   │   ├── biometric_credential.py # WebAuthn FIDO2 credentials
    │   │   ├── merchant.py            # Merchant accounts
    │   │   ├── bank_account.py        # Linked payment accounts
    │   │   ├── auth_log.py            # Authentication audit trail
    │   │   ├── enrollment_log.py      # Enrollment events
    │   │   ├── verification_log.py    # Verification events
    │   │   ├── audit_log.py           # System-wide audit log (JSONB)
    │   │   └── trust_engine.py        # 10 Trust Engine tables          ★ NEW
    │   ├── services/                  # Business logic & ML inference (20 services)
    │   │   ├── face_detector.py       # InsightFace buffalo_l detection
    │   │   ├── face_embedding.py      # ArcFace 512-d embeddings
    │   │   ├── liveness_service.py    # MediaPipe EAR/yaw liveness
    │   │   ├── liveness_pipeline.py   # 6-stage weighted liveness pipeline
    │   │   ├── anti_spoof_service.py  # MiniFASNet ONNX anti-spoofing
    │   │   ├── iris_service.py        # Gabor IrisCode + Hamming Distance
    │   │   ├── fingerprint_service.py # ISO minutiae extraction + MCC
    │   │   ├── fusion_engine.py       # Score-level biometric fusion
    │   │   ├── payment_service.py     # Payment authorization orchestrator
    │   │   ├── enrollment_service.py  # Enrollment pipeline
    │   │   ├── verification_service.py # 7-step verification pipeline
    │   │   ├── firebase_service.py    # Firebase ID token verification
    │   │   ├── passive_liveness_service.py  # MiniFASNetV1+V2 ensemble  ★ NEW
    │   │   ├── active_liveness_service.py   # Challenge-response liveness ★ NEW
    │   │   ├── emotion_service.py           # MobileNetV3 emotion recog  ★ NEW
    │   │   ├── headpose_service.py          # solvePnP 3D pose estimation ★ NEW
    │   │   ├── eye_tracking_service.py      # MediaPipe Iris tracking     ★ NEW
    │   │   ├── depth_estimation_service.py  # MiDaS / DPT depth maps     ★ NEW
    │   │   ├── challenge_ai_service.py      # Anti-spoof challenge AI     ★ NEW
    │   │   ├── deepfake_service.py          # EfficientNet-B4 deepfake    ★ NEW
    │   │   ├── device_trust_service.py      # Device integrity scoring    ★ NEW
    │   │   ├── behavioral_biometrics_service.py # IsolationForest behavior ★ NEW
    │   │   ├── risk_scoring_service.py      # NeoFace Trust Score engine  ★ NEW
    │   │   └── continuous_auth_service.py   # Continuous auth state machine ★ NEW
    │   ├── repositories/              # Async data access layer (7 repos)
    │   ├── schemas/                   # Pydantic v2 request/response models
    │   ├── tasks/                     # Celery background workers          ★ NEW
    │   │   ├── celery_app.py          # Celery app + beat schedule
    │   │   ├── continuous_auth_tasks.py # 30s session sweep
    │   │   └── cleanup_tasks.py       # Log retention + cleanup
    │   └── main.py                    # FastAPI app factory + lifespan
    ├── migrations/
    │   └── versions/
    │       └── 0002_trust_engine_tables.py  # Trust Engine migration    ★ NEW
    ├── Dockerfile                     # Multi-stage Python 3.12 build
    ├── requirements.txt               # 35 pinned dependencies
    └── alembic.ini                    # Database migration config
├── start.sh                           # Smart Docker startup script       ★ NEW
└── cleanup.sh                         # Docker storage reclaimer          ★ NEW
```

---

## ✨ Features

### 🔐 Core Biometric Engine

| Feature | Details |
|---|---|
| **Face Recognition** | InsightFace `buffalo_l` · ArcFace 512-d embeddings · Cosine similarity 1:N search · <150ms |
| **Multi-image Enrollment** | 1–5 images per user · Quality validation · Blur detection · Embedding averaging |
| **Face Verification** | 7-step pipeline: detect → liveness → embed → 1:N search → user validate → log |
| **Iris Recognition** | Daugman rubber sheet normalization · 2D Gabor IrisCode · Masked Hamming Distance |
| **Fingerprint Recognition** | ISO/IEC 19794-2 minutiae extraction · CLAHE enhancement · MCC-style matching |
| **Biometric Fusion** | Score-level fusion: Face 45% + Iris 35% + Fingerprint 20% · Auto-renormalization |

---

### 🛡 Trust Engine — 15 Modules ★ NEW

#### Module 1 — Passive Liveness Detection
Detects spoof attacks without any user action.

| Attack Type | Detection Method |
|---|---|
| Printed photos | MiniFASNetV1 + V2 ensemble (ONNX) |
| Phone/tablet replay | Frequency artifact analysis |
| Screen replay | Texture complexity + saturation |
| Face masks | Depth + gradient variance |
| Virtual camera injection | Brightness + sharpness anomaly |
| Static image injection | LBP variance + histogram entropy |

**Models:** MiniFASNetV1 · MiniFASNetV2 · Texture heuristic fallback  
**Output:** `{ "liveness_score": 0.97, "is_live": true, "confidence": 98 }`  
**Endpoint:** `POST /api/v1/liveness/check`

---

#### Module 2 — Active Liveness (Challenge-Response)
Randomized human interaction challenges that can't be pre-recorded.

**Supported actions:** Blink · Smile · Open mouth · Turn left/right · Raise eyebrows · Look up/down  
**Challenge Engine:** 10 multi-step challenges, never repeating consecutively  
**Tracking:** MediaPipe FaceMesh — 468 facial landmarks  
**Output:** `{ "challenge_completed": true, "challenge_type": "blink_twice" }`  
**Endpoint:** `POST /api/v1/liveness/challenge` + `POST /api/v1/liveness/verify`

---

#### Module 3 — Emotion Recognition
Secondary liveness signal via facial emotion classification.

**Detects:** Happy · Neutral · Surprise · Angry · Sad · Fear · Disgust  
**Model:** MobileNetV3 trained on FER2013 + AffectNet  
**Output:** `{ "emotion": "happy", "confidence": 96 }`  
**Endpoint:** `POST /api/v1/emotion/analyze`

---

#### Module 4 — Head Pose Estimation
Verifies 3D face movement to detect flat-surface attacks.

**Calculates:** Pitch (up/down) · Roll (tilt) · Yaw (left/right)  
**Method:** MediaPipe FaceMesh + OpenCV `solvePnP` (6-point 3D model)  
**Output:** `{ "pitch": 12, "yaw": -17, "roll": 4 }`  
**Endpoint:** `POST /api/v1/headpose`

---

#### Module 5 — Eye Tracking
Detects unnatural eye behavior indicating replay or injection attacks.

**Tracks:** EAR (Eye Aspect Ratio) · Blink rate · Gaze direction · Pupil movement · Iris position  
**Detects:** Frozen eyes · Static video replay · Unnaturally centered irises  
**Method:** MediaPipe Iris (468 landmarks + 10 iris refinement points)  
**Output:** `{ "gaze_direction": "left", "blink_detected": true, "eye_confidence": 95 }`

---

#### Module 6 — Depth Estimation
Differentiates real 3D faces from flat images and screen replays.

**Models:** MiDaS Small (256×256) · DPT Hybrid (384×384) · Gradient heuristic fallback  
**Output:** `{ "depth_score": 0.94, "is_3d_face": true }`

---

#### Module 7 — Challenge AI
Intelligent anti-spoof challenge generator with history-aware anti-repeat logic.

- Never repeats the same challenge sequence consecutively
- Maintains per-session challenge history (Redis-backed, in-memory fallback)
- Challenge nonces for one-time use (anti-replay protection)
- 60-second challenge expiry window
- 10 challenge types across easy/medium difficulty levels
- Challenges stored in `challenge_logs` for audit

---

#### Module 8 — Deepfake Detection
Detects AI-generated and manipulated faces.

| Attack | Detected By |
|---|---|
| Face swap (DeepFaceLab, FaceSwap) | EfficientNet-B4 frequency artifacts |
| GAN faces (StyleGAN, DALL-E) | XceptionNet texture anomaly |
| Synthetic avatars | Smoothness + DCT coefficient analysis |
| AI video manipulation | Checkerboard transposed-conv artifacts |

**Models:** EfficientNet-B4 (primary, 60%) · XceptionNet (secondary, 40%) · Frequency heuristic fallback  
**Training data:** FaceForensics++ · DeepFakeBench  
**Output:** `{ "deepfake_probability": 0.04, "is_deepfake": false }`  
**Endpoint:** `POST /api/v1/deepfake/check`

---

#### Module 9 — Device Integrity
Trust scoring for the requesting device.

**Android:** Root · Magisk · USB debugging · Emulator (BlueStacks, Genymotion) · Root file detection  
**iOS:** Jailbreak · Cydia file detection · Debug mode · iOS Simulator  
**Web:** Virtual camera (OBS, ManyCam) · Selenium/WebDriver · Headless Chrome · Puppeteer · Playwright · Software WebGL renderer  

**Output:** `{ "device_trust": 91, "rooted": false, "emulator": false }`  
**Endpoint:** `POST /api/v1/device/assess`

---

#### Module 10 — Behavioral Biometrics
Builds unique behavioral profiles per user with 3-phase anomaly detection.

| Phase | Algorithm | Activation |
|---|---|---|
| Phase 1 | Rule-Based (human range validation) | Immediate |
| Phase 2 | Isolation Forest (z-score anomaly) | After 20 events |
| Phase 3 | XGBoost (supervised classification) | Roadmap |

**Mouse:** Speed · Curvature · Hesitation rate  
**Keyboard:** Typing WPM · Dwell time · Flight time  
**Touch:** Swipe velocity · Touch pressure · Gesture rhythm  

**Output:** `{ "behavior_score": 93 }`  
**Endpoints:** `POST /api/v1/behavior/events` · `POST /api/v1/behavior/score` · `GET /api/v1/behavior/profile`

---

#### Module 11 — NeoFace Trust Score (Risk Engine)
Composite 0–100 trust score from all biometric and contextual signals.

```
Trust Score = Σ(weight_i × score_i) for all available signals

Default weights:
  Face Score         25%
  Liveness Score     20%
  Deepfake Score     15%
  Behavior Score     15%
  Device Trust       15%
  Location Trust      5%
  Fingerprint Trust   5%
```

**Decision Rules:**

| Score | Decision | Action |
|---|---|---|
| 90 – 100 | ✅ Approve | Allow transaction/session |
| 70 – 89 | ⚠️ Step-Up | Request additional auth factor |
| < 70 | ❌ Reject | Block the transaction |

**Hard Block Conditions (override score):**
- Deepfake score < 5 → immediate reject
- Liveness score < 10 → immediate reject
- Device trust = 0 → immediate reject

**Endpoint:** `POST /api/v1/risk/score`

---

#### Module 12 — Continuous Authentication
Verifies user authenticity every 30 seconds after login.

**Checks each interval:**
1. Face presence detection (passive liveness)
2. Eye tracking (frozen eye detection)
3. Device trust validation
4. Behavioral monitoring

**Session lifecycle:**
```
active → reauth_required (score < 70) → active (after successful reauth)
       → suspended (score < 50)
       → terminated (score < 30 OR 3 consecutive failed reauths)
```

**Celery beat:** Sweeps all active sessions every 30 seconds, applying score decay for missed checks.  
**Endpoints:** `POST /api/v1/continuous-auth/session/start` · `/check` · `/end` · `GET /session/{token}`

---

### 💳 Payment Infrastructure

| Feature | Details |
|---|---|
| **Biometric Payment Auth** | Multi-modal: Face + Iris + Fingerprint fusion |
| **WebAuthn / FIDO2** | Touch ID · Face ID · Windows Hello · Passkeys |
| **Risk-Tiered Payments** | Low/Medium/High tiers based on transaction amount |
| **Merchant Management** | API key generation (bcrypt-hashed) · KYB verification |
| **Bank Account Linking** | Tokenized (Plaid/Stripe) · No raw account numbers stored |
| **Transaction Audit** | Full biometric breakdown per transaction |

---

### 👤 User Management

- Email/password registration with bcrypt (rounds=12)
- Google OAuth via Firebase → NeoFace JWT sync
- Admin user bootstrap on startup
- Role-based access control (user / admin / superadmin)
- Multi-modal enrollment status tracking (face / iris / fingerprint)
- GDPR-compliant biometric erasure endpoints

---

### 📊 Admin Dashboard

| Section | What You See |
|---|---|
| **Overview** | Total users, enrolled, active, enrollment rate, auth success % |
| **Analytics** | Daily verification volume, modality breakdown, failure reasons |
| **Payment Overview** | Daily volume, authorization rate, average fusion score |
| **Auth Logs** | Paginated verification history with confidence + liveness scores |
| **User Management** | Full CRUD, enrollment status, soft-delete |
| **Health Check** | Database connectivity, service status |

---

### 🔒 Security Architecture

| Layer | Implementation |
|---|---|
| **Authentication** | JWT (HS256) · 30-min access / 7-day refresh tokens |
| **Password Hashing** | bcrypt cost factor 12 |
| **Transport Security** | TLS 1.3 (production) |
| **Rate Limiting** | slowapi per-IP limits (10 verifications/min, 5 enrollments/min) |
| **Audit Logging** | Structured JSON logs for every biometric event |
| **Data Minimization** | Embeddings only — no raw face images stored permanently |
| **Anti-Spoof** | MiniFASNet ONNX + texture heuristic fallback |
| **Anti-Deepfake** | EfficientNet-B4 + XceptionNet ensemble |
| **Challenge Nonces** | One-time use, 60-second TTL, Redis-backed |
| **WebAuthn** | FIDO2 — private keys never leave device secure enclave |

**What NeoFace NEVER stores:**
- Raw fingerprint images
- Raw biometric video
- Plaintext passwords
- Full account numbers

---

## 🖥 Frontend

### Pages & Routes

| Route | Description |
|---|---|
| `/` | Animated landing page with 3D biometric visualizations |
| `/login` | JWT + Google OAuth login |
| `/register` | Account creation |
| `/enroll` | Guided face enrollment wizard (webcam capture) |
| `/verify` | Real-time face verification interface |
| `/checkout-demo` | Live biometric payment demonstration |
| `/dashboard` | Admin analytics overview |
| `/dashboard/analytics` | Recharts time-series analytics |
| `/dashboard/users` | User management table |
| `/dashboard/logs` | Auth + verification audit logs |
| `/dashboard/bank-accounts` | Linked payment methods |
| `/dashboard/fingerprint` | WebAuthn device management |
| `/dashboard/identity` | Identity verification panel |
| `/dashboard/settings` | System configuration |

### Visual Components

| Component | Description |
|---|---|
| `BiometricOrbit` | 3D orbital animation (Three.js + React Three Fiber) |
| `BiometricWorkflow` | Animated workflow diagram |
| `FaceMeshCanvas` | Real-time face mesh overlay canvas |
| `FaceScanVisual` | Biometric scan animation |
| `FloatingCard` | Floating UI card with motion effects |
| `IdentityCore` | 3D identity visualization |

### Landing Sections

| Section | Description |
|---|---|
| `HeroSection` | Full-screen hero with 3D animation + GSAP scroll |
| `ArchitectureSection` | System architecture visualization |
| `ModalitiesSection` | Face, Iris, Fingerprint modality cards |
| `ProductSection` | Feature showcase |
| `SecuritySection` | Security highlights |
| `DeveloperSection` | API documentation preview |
| `ScrollStory` | Scroll-driven narrative animation (Lenis) |
| `FinalCTA` | Call-to-action section |

---

## 🗄 Database Schema

### Core Tables (12)

| Table | Purpose |
|---|---|
| `users` | Identity records · roles · enrollment status |
| `face_embeddings` | ArcFace 512-d vectors (Float array) |
| `iris_embeddings` | Gabor IrisCode (LargeBinary 256B) |
| `fingerprint_templates` | ISO/IEC 19794-2 templates |
| `biometric_credentials` | WebAuthn FIDO2 public keys |
| `transactions` | Payment records with fusion scores |
| `transaction_biometric_details` | Per-modality scores per transaction |
| `merchants` | Business accounts + API keys |
| `bank_accounts` | Tokenized payment methods |
| `auth_logs` | Authentication attempt history |
| `enrollment_logs` | Enrollment pipeline events |
| `verification_logs` | Verification pipeline events |
| `audit_logs` | System-wide JSONB audit trail |

### Trust Engine Tables (10) ★ NEW

| Table | Purpose |
|---|---|
| `liveness_logs` | Every passive + active liveness attempt |
| `emotion_logs` | Emotion analysis results |
| `headpose_logs` | Pitch/roll/yaw measurement history |
| `deepfake_logs` | Deepfake detection audit (image hash only) |
| `behavior_profiles` | Per-user behavioral baseline (EMA) |
| `behavior_events` | Individual behavioral data points |
| `device_trust_logs` | Device integrity assessment history |
| `risk_scores` | NeoFace Trust Score history |
| `continuous_sessions` | Active continuous auth sessions |
| `challenge_logs` | Anti-spoof challenge history |

---

## 🛠 Tech Stack

### Backend

| Category | Technology | Version |
|---|---|---|
| **Language** | Python | 3.12 |
| **Framework** | FastAPI | 0.115.5 |
| **ASGI Server** | Uvicorn + uvloop + httptools | 0.32.1 |
| **Database ORM** | SQLAlchemy (async) | 2.0.36 |
| **Database Driver** | asyncpg | 0.30.0 |
| **Database** | PostgreSQL (Supabase) | 16 |
| **Migrations** | Alembic | 1.14.0 |
| **Validation** | Pydantic v2 + pydantic-settings | 2.10.3 |
| **Auth** | python-jose (JWT) + bcrypt | 3.3.0 / 4.2.1 |
| **OAuth** | Firebase Admin SDK | 6.6.0 |
| **WebAuthn** | py_webauthn | 2.1.0 |
| **Cache** | Redis (hiredis) | 7.2 / 5.2.1 |
| **Task Queue** | Celery | 5.4.0 |
| **Rate Limiting** | slowapi | 0.1.9 |
| **Logging** | Loguru | 0.7.3 |
| **Face Recognition** | InsightFace (buffalo_l) | 0.7.3 |
| **ML Inference** | ONNX Runtime | 1.20.1 |
| **Computer Vision** | OpenCV (headless) | 4.10.0 |
| **Facial Landmarks** | MediaPipe | 0.10.18 |
| **Deep Learning** | PyTorch (CPU) | 2.5.1 |
| **Anomaly Detection** | scikit-learn (IsolationForest) | 1.5.2 |
| **Gradient Boosting** | XGBoost | 2.1.3 |
| **Encryption** | cryptography (AES-256-GCM) | 43.0.3 |
| **HTTP Client** | httpx | 0.27.2 |
| **Storage** | Supabase Storage / AWS S3 / Local | — |

### Frontend

| Category | Technology | Version |
|---|---|---|
| **Language** | TypeScript | 5.7 |
| **Framework** | Next.js (App Router) | 16.2.9 |
| **UI Library** | React | 19.0.0 |
| **Styling** | Tailwind CSS | 3.4.17 |
| **Animation** | Framer Motion | 11.15.0 |
| **3D Engine** | Three.js + React Three Fiber | 0.184.0 / 9.6.1 |
| **3D Helpers** | @react-three/drei | 10.7.7 |
| **Post-processing** | @react-three/postprocessing | 3.0.4 |
| **Scroll** | GSAP + Lenis (smooth scroll) | 3.15.0 / 1.3.23 |
| **State** | Zustand | 5.0.2 |
| **Data Fetching** | TanStack Query (React Query) | 5.62.0 |
| **Forms** | React Hook Form + Zod | 7.54.1 / 3.23.8 |
| **HTTP** | Axios | 1.7.9 |
| **Charts** | Recharts | 3.8.1 |
| **UI Primitives** | Radix UI | Multiple |
| **Icons** | Lucide React | 0.468.0 |
| **Fonts** | Geist (Vercel) | 1.3.1 |
| **Auth** | Firebase | 12.14.0 |
| **Notifications** | Sonner | 1.7.1 |
| **Date Utils** | date-fns | 4.1.0 |

### Infrastructure

| Service | Technology |
|---|---|
| **Container** | Docker (multi-stage Python 3.12-slim) |
| **Orchestration** | Docker Compose |
| **Background Jobs** | Celery + Redis Broker |
| **Task Monitoring** | Flower UI |
| **Frontend Hosting** | Vercel |
| **Database Hosting** | Supabase (PostgreSQL) |
| **Secret Management** | Environment variables (`.env`) |

---

## 📡 API Reference

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/login` | OAuth2 password flow → JWT pair |
| `POST` | `/api/v1/auth/register` | Email/password registration |
| `POST` | `/api/v1/auth/refresh` | Refresh access token |
| `GET` | `/api/v1/auth/me` | Current user profile |
| `POST` | `/api/v1/auth/google` | Firebase token → NeoFace JWT |
| `POST` | `/api/v1/auth/logout` | Client-side logout |

### Biometric Enrollment
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/enrollment` | Multi-image face enrollment (1–5 images) |
| `GET` | `/api/v1/enrollment/{user_id}` | Enrollment status |
| `DELETE` | `/api/v1/enrollment/{user_id}` | Delete face data (admin) |
| `POST` | `/api/v1/biometrics/enroll/iris` | Iris enrollment |
| `POST` | `/api/v1/biometrics/enroll/fingerprint` | Fingerprint enrollment |
| `GET` | `/api/v1/biometrics/status` | All modality enrollment status |
| `DELETE` | `/api/v1/biometrics/iris` | GDPR iris erasure |
| `DELETE` | `/api/v1/biometrics/fingerprint` | GDPR fingerprint erasure |

### Verification
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/verify` | 1:N face identification + liveness |
| `POST` | `/api/v1/biometrics/verify/iris` | Iris verification |
| `POST` | `/api/v1/biometrics/verify/fingerprint` | Fingerprint verification |

### Payments
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/payments/authorize` | Biometric payment authorization |
| `GET` | `/api/v1/payments/history` | Paginated transaction history |
| `GET` | `/api/v1/payments/{id}` | Single transaction detail |
| `GET` | `/api/v1/payments/admin/all` | All transactions (admin) |

### WebAuthn / FIDO2
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/webauthn/register/begin` | Start device registration |
| `POST` | `/api/v1/webauthn/register/complete` | Complete device registration |
| `POST` | `/api/v1/webauthn/authenticate/begin` | Start device auth |
| `POST` | `/api/v1/webauthn/authenticate/complete` | Complete device auth |
| `GET` | `/api/v1/webauthn/devices` | List enrolled devices |
| `PATCH` | `/api/v1/webauthn/devices/{id}` | Rename device |
| `DELETE` | `/api/v1/webauthn/devices/{id}` | Revoke device |
| `PATCH` | `/api/v1/webauthn/devices/{id}/payments` | Toggle payment signing |
| `POST` | `/api/v1/webauthn/payment/begin` | Start payment signing |
| `POST` | `/api/v1/webauthn/payment/complete` | Complete payment signing |

### Trust Engine ★ NEW
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/liveness/check` | Passive liveness detection |
| `POST` | `/api/v1/liveness/challenge` | Generate active liveness challenge |
| `POST` | `/api/v1/liveness/verify` | Verify challenge frame |
| `POST` | `/api/v1/emotion/analyze` | Facial emotion analysis |
| `POST` | `/api/v1/headpose` | Head pose estimation (pitch/roll/yaw) |
| `POST` | `/api/v1/deepfake/check` | Deepfake detection |
| `POST` | `/api/v1/device/assess` | Device integrity scoring |
| `POST` | `/api/v1/behavior/events` | Submit behavioral events |
| `POST` | `/api/v1/behavior/score` | Real-time behavioral score |
| `GET` | `/api/v1/behavior/profile` | User behavioral baseline |
| `POST` | `/api/v1/risk/score` | NeoFace Trust Score |
| `GET` | `/api/v1/risk/history` | Trust score history |
| `POST` | `/api/v1/continuous-auth/session/start` | Start continuous auth session |
| `POST` | `/api/v1/continuous-auth/session/check` | Submit periodic check frame |
| `POST` | `/api/v1/continuous-auth/session/end` | Terminate session |
| `GET` | `/api/v1/continuous-auth/session/{token}` | Get session status |

### Admin
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/dashboard/users` | User statistics |
| `GET` | `/api/v1/dashboard/verifications` | Verification statistics |
| `GET` | `/api/v1/dashboard/success-rate` | Auth success percentage |
| `GET` | `/api/v1/dashboard/logs` | Paginated auth logs |
| `GET` | `/api/v1/dashboard/analytics` | Daily time-series |
| `GET` | `/api/v1/dashboard/payments/overview` | Payment metrics |
| `GET` | `/api/v1/dashboard/payments/daily` | Daily payment volume |
| `GET` | `/api/v1/dashboard/payments/recent` | Live transaction feed |
| `GET` | `/api/v1/dashboard/health` | Database health check |

> **Full interactive Swagger docs:** `http://localhost:8000/docs`  
> **ReDoc docs:** `http://localhost:8000/redoc`

---

## ⚡ Quick Start

### Prerequisites
- Docker 24+ and Docker Compose v2
- Node.js 18+ and npm
- Python 3.12+
- 8 GB RAM (AI models require significant memory)
- Git

> **New contributors:** See the detailed [SETUP.md](./SETUP.md) guide for step-by-step instructions.

### 1. Clone

```bash
git clone https://github.com/DivyeBhatnagar/NeoFace.git
cd NeoFace
```

### 2. Configure Environment

```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env — set JWT_SECRET, ADMIN_PASSWORD, and optionally DATABASE_URL

# Frontend
cp frontend/.env.example frontend/.env.local
# Set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 (already the default)
```

### 3. Start NeoFace (Smart Startup)

```bash
# Quick way (recommended):
make setup   # copies env files, installs frontend deps, shows model status
make models  # download all ONNX models (~770 MB)
make start   # start all services

# Or manually:
chmod +x start.sh cleanup.sh
python3 backend/scripts/download_models.py --all
./start.sh
```

- Backend available at `http://localhost:8000/docs`
- Frontend available at `http://localhost:3000`
- Celery Flower available at `http://localhost:5555`

First startup takes ~3–5 minutes to build Docker and download InsightFace models. Subsequent runs are near-instant.

### 4. Run Database Migrations (First Run Only)

```bash
make migrate
# OR:
docker compose exec api alembic upgrade head
```

### 5. Managing Storage

As NeoFace uses large Docker images, we provide a cleanup utility to keep your Mac's storage free from dangling layers and unused containers:

```bash
./cleanup.sh          # Safe prune (dangling images & stopped containers)
./cleanup.sh --status # View current Docker disk usage
./cleanup.sh --deep   # Nuclear option (resets local DB and deletes all images)
```

### 6. Admin Credentials

Default admin account (change in `backend/.env`):
```
Email:    admin@neoface.io
Password: (whatever you set as ADMIN_PASSWORD in backend/.env)
```

---

## 📦 Docker Services

```yaml
# docker-compose.yml
services:
  postgres   # PostgreSQL 16 — primary data store
  redis      # Redis 7.2 — Celery broker + challenge cache + session store
  api        # NeoFace FastAPI backend (port 8000)
  worker     # Celery worker (4 concurrent, 3 queues)
  beat       # Celery beat scheduler (30s continuous auth sweep)
  flower     # Celery monitoring UI (port 5555, admin:neoface_flower_pass)
```

---

## 🚀 Deployment

### Frontend → Vercel

```bash
cd frontend
vercel deploy
```

**Required env vars:**
```
NEXT_PUBLIC_API_BASE_URL=https://your-api.domain.com
```

### Backend → Railway / Render / AWS

The `Dockerfile` is production-ready with:
- Multi-stage build (builder + runtime)
- Non-root `neoface` user
- Health check endpoint
- uvicorn with uvloop + httptools

**Required env vars for production:**
```bash
JWT_SECRET=<64-char random secret>
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
ENVIRONMENT=production
ANTI_SPOOF_ENABLED=true
USE_LIVENESS_PIPELINE=true
```

### Model Files

Download ONNX models to `backend/models/`:
```bash
cd backend
python3 scripts/download_models.py --all
```

```
backend/models/
├── anti_spoof.onnx              # MiniFASNet (1.7 MB)
├── MiniFASNetV1.onnx            # Trust Engine V1 (1.7 MB)
├── MiniFASNetV2.onnx            # Trust Engine V2 (1.7 MB)
├── emotion_mobilenetv3.onnx     # Emotion recognition (33 MB)
├── midas_small.onnx             # Depth estimation fast (63 MB)
├── dpt_hybrid.onnx              # Depth estimation high-quality (508 MB)
├── efficientnet_b4_deepfake.onnx # Deepfake detection primary (83 MB)
└── xceptionnet_deepfake.onnx    # Deepfake detection secondary (85 MB)
```

> All services have heuristic fallbacks and will run without model files, using CPU-based feature extraction instead.

---

## 📈 Performance Targets

| Operation | Target | Method |
|---|---|---|
| Face Recognition | < 150ms | ArcFace cosine similarity |
| Passive Liveness | < 300ms | MiniFASNet ONNX (CPU) |
| Active Liveness Frame | < 100ms | MediaPipe FaceMesh |
| Deepfake Detection | < 500ms | EfficientNet-B4 ONNX |
| Trust Score | < 50ms | Pure computation |
| Concurrent Users | 1,000+ | async FastAPI + uvloop |

---

## 📁 Environment Variables

See [`backend/.env.example`](./backend/.env.example) for the full list of 50+ configuration options including:

- `JWT_SECRET` — minimum 32 characters
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `FIREBASE_CREDENTIALS_JSON` — Firebase service account JSON
- `ANTI_SPOOF_MODEL_PATH` — MiniFASNet ONNX path
- `SIMILARITY_THRESHOLD` — ArcFace match threshold (default: 0.65)
- `LIVENESS_THRESHOLD` — Liveness pass threshold (default: 60.0)
- `RISK_APPROVE_THRESHOLD` — Trust Score approve threshold (default: 90.0)
- `CONTINUOUS_AUTH_CHECK_INTERVAL` — Seconds between checks (default: 30)

---

## 🗺 Roadmap

- [ ] `pgvector` ANN search for sub-10ms 1:N embedding lookup at scale
- [ ] WebRTC live video stream support for continuous biometric capture
- [ ] Mobile SDK (React Native) with device-native liveness
- [ ] XGBoost Phase 3 behavioral model training pipeline
- [ ] Multi-tenant merchant isolation with row-level security
- [ ] Biometric payment Rails integration (UPI, SEPA, ACH)
- [ ] Hardware security module (HSM) key storage integration

---

## 📄 License

**Proprietary** — NeoFace © 2026. All rights reserved.

For licensing inquiries: [engineering@neoface.io](mailto:engineering@neoface.io)

---

<div align="center">

Built with precision for the post-password world.

**NeoFace** · Biometric Identity Infrastructure

</div>
