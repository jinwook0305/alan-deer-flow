import {
  CompassIcon,
  GraduationCapIcon,
  ImageIcon,
  MicroscopeIcon,
  PenLineIcon,
  ShapesIcon,
  SparklesIcon,
  VideoIcon,
} from "lucide-react";

import type { Translations } from "./types";

export const koKR: Translations = {
  // Locale meta
  locale: {
    localName: "한국어",
  },

  // Common
  common: {
    home: "홈",
    settings: "설정",
    delete: "삭제",
    edit: "편집",
    rename: "이름 변경",
    share: "공유",
    openInNewWindow: "새 창에서 열기",
    close: "닫기",
    more: "더보기",
    search: "검색",
    loadMore: "더 불러오기",
    download: "다운로드",
    thinking: "생각 중",
    artifacts: "아티팩트",
    public: "공개",
    custom: "사용자 정의",
    notAvailableInDemoMode: "데모 모드에서는 사용할 수 없습니다",
    loading: "불러오는 중...",
    version: "버전",
    lastUpdated: "최종 업데이트",
    code: "코드",
    preview: "미리보기",
    cancel: "취소",
    save: "저장",
    install: "설치",
    create: "만들기",
    import: "가져오기",
    export: "내보내기",
    exportAsMarkdown: "Markdown으로 내보내기",
    exportAsJSON: "JSON으로 내보내기",
    exportSuccess: "대화를 내보냈습니다",
  },

  // Home
  home: {
    docs: "문서",
    blog: "블로그",
  },

  // Welcome
  welcome: {
    greeting: "다시 만나서 반가워요!",
    description:
      "오픈소스 슈퍼 에이전트, 🦌 DeerFlow에 오신 것을 환영합니다. 내장 및 사용자 정의 스킬을 통해 웹 검색, 데이터 분석, 슬라이드·웹페이지 등 다양한 아티팩트 생성을 도와드립니다.",

    createYourOwnSkill: "나만의 스킬 만들기",
    createYourOwnSkillDescription:
      "나만의 스킬을 만들어 DeerFlow의 능력을 끌어올리세요. 맞춤형 스킬로\nDeerFlow는 웹 검색, 데이터 분석, 슬라이드·웹페이지 같은\n아티팩트 생성 등 거의 모든 작업을 도와줄 수 있습니다.",
  },

  // Clipboard
  clipboard: {
    copyToClipboard: "클립보드에 복사",
    copiedToClipboard: "클립보드에 복사되었습니다",
    failedToCopyToClipboard: "클립보드 복사에 실패했습니다",
    linkCopied: "링크가 클립보드에 복사되었습니다",
  },

  // Input Box
  inputBox: {
    placeholder: "오늘은 어떤 도움이 필요하신가요?",
    createSkillPrompt:
      "`skill-creator`로 새로운 스킬을 단계별로 만들어 봅시다. 먼저, 이 스킬이 어떤 일을 하길 원하시나요?",
    addAttachments: "첨부 파일 추가",
    mode: "모드",
    chatMode: "채팅",
    chatModeDescription:
      "도구도, 스킬도 없는 순수 LLM 채팅 — 멀티턴 대화만 가능",
    chatMemory: "메모리",
    chatMemoryOn: "켜기",
    chatMemoryOff: "끄기",
    tools: "도구",
    toolGroups: {
      web: "웹 (검색, 가져오기)",
      "file:read": "파일 읽기",
      "file:write": "파일 쓰기",
      bash: "Bash",
    },
    flashMode: "Flash",
    flashModeDescription: "빠르고 효율적이지만 정확하지 않을 수 있습니다",
    reasoningMode: "추론",
    reasoningModeDescription:
      "행동 전에 추론하여 시간과 정확도의 균형을 맞춥니다",
    proMode: "Pro",
    proModeDescription:
      "추론·계획·실행을 거쳐 더 정확한 결과를 제공하며, 시간이 더 걸릴 수 있습니다",
    ultraMode: "Ultra",
    ultraModeDescription:
      "서브에이전트로 작업을 분담하는 Pro 모드 — 복잡한 다단계 작업에 가장 적합합니다",
    reasoningEffort: "추론 강도",
    reasoningEffortMinimal: "최소",
    reasoningEffortMinimalDescription: "검색 + 직접 출력",
    reasoningEffortLow: "낮음",
    reasoningEffortLowDescription: "단순 논리 검사 + 얕은 추론",
    reasoningEffortMedium: "보통",
    reasoningEffortMediumDescription: "다층 논리 분석 + 기본 검증",
    reasoningEffortHigh: "높음",
    reasoningEffortHighDescription:
      "전방위 논리 추론 + 다중 경로 검증 + 역방향 확인",
    searchModels: "모델 검색...",
    surpriseMe: "랜덤",
    surpriseMePrompt: "랜덤으로 추천해줘",
    followupLoading: "후속 질문 생성 중...",
    followupConfirmTitle: "제안을 보낼까요?",
    followupConfirmDescription:
      "입력란에 이미 텍스트가 있습니다. 어떻게 보낼지 선택하세요.",
    followupConfirmAppend: "이어 붙여 보내기",
    followupConfirmReplace: "교체해서 보내기",
    suggestions: [
      {
        suggestion: "작성",
        prompt: "[주제]에 대한 최신 트렌드를 다룬 블로그 글을 작성해줘",
        icon: PenLineIcon,
      },
      {
        suggestion: "리서치",
        prompt: "[주제]에 대해 심층 리서치를 수행하고 결과를 요약해줘.",
        icon: MicroscopeIcon,
      },
      {
        suggestion: "수집",
        prompt: "[출처]에서 데이터를 수집해 보고서를 만들어줘.",
        icon: ShapesIcon,
      },
      {
        suggestion: "학습",
        prompt: "[주제]에 대해 알려주고 튜토리얼을 만들어줘.",
        icon: GraduationCapIcon,
      },
    ],
    suggestionsCreate: [
      {
        suggestion: "웹페이지",
        prompt: "[주제]에 대한 웹페이지를 만들어줘",
        icon: CompassIcon,
      },
      {
        suggestion: "이미지",
        prompt: "[주제]에 대한 이미지를 만들어줘",
        icon: ImageIcon,
      },
      {
        suggestion: "동영상",
        prompt: "[주제]에 대한 동영상을 만들어줘",
        icon: VideoIcon,
      },
      {
        type: "separator",
      },
      {
        suggestion: "스킬",
        prompt:
          "`skill-creator`로 새로운 스킬을 단계별로 만들어 봅시다. 먼저, 이 스킬이 어떤 일을 하길 원하시나요?",
        icon: SparklesIcon,
      },
    ],
  },

  // Sidebar
  sidebar: {
    newChat: "새 채팅",
    chats: "채팅",
    recentChats: "최근 채팅",
    demoChats: "데모 채팅",
    agents: "에이전트!!",
  },

  // Agents
  agents: {
    title: "에이전트",
    description:
      "전용 프롬프트와 기능을 갖춘 사용자 정의 에이전트를 만들고 관리하세요.",
    newAgent: "새 에이전트",
    emptyTitle: "사용자 정의 에이전트가 아직 없습니다",
    emptyDescription:
      "전용 시스템 프롬프트를 가진 첫 번째 사용자 정의 에이전트를 만들어 보세요.",
    chat: "채팅",
    delete: "삭제",
    deleteConfirm:
      "이 에이전트를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.",
    deleteSuccess: "에이전트가 삭제되었습니다",
    newChat: "새 채팅",
    createPageTitle: "에이전트 설계하기",
    createPageSubtitle:
      "원하는 에이전트를 설명해 주세요 — 대화를 통해 만들어 드릴게요.",
    nameStepTitle: "새 에이전트 이름 지정",
    nameStepHint:
      "영문, 숫자, 하이픈만 사용 — 소문자로 저장됩니다 (예: code-reviewer)",
    nameStepPlaceholder: "예: code-reviewer",
    nameStepContinue: "계속",
    nameStepInvalidError:
      "잘못된 이름입니다 — 영문, 숫자, 하이픈만 사용하세요",
    nameStepAlreadyExistsError: "같은 이름의 에이전트가 이미 존재합니다",
    nameStepNetworkError:
      "네트워크 요청 실패 — 네트워크 또는 백엔드 연결을 확인하세요",
    nameStepCheckError:
      "이름 사용 가능 여부를 확인할 수 없습니다 — 다시 시도해 주세요",
    nameStepApiDisabledError:
      "이 서버에서는 사용자 정의 에이전트 관리가 활성화되어 있지 않습니다. 관리자에게 문의하세요.",
    nameStepBootstrapMessage:
      "새 사용자 정의 에이전트의 이름은 {name}입니다. 저장 전에 목적, 동작, SOUL.md를 함께 설계해 주세요.",
    save: "에이전트 저장",
    saving: "에이전트 저장 중...",
    saveRequested:
      "저장이 요청되었습니다. DeerFlow가 초기 버전을 생성·저장하고 있습니다.",
    saveHint:
      "초안 상태라도 우측 상단 메뉴에서 언제든지 이 에이전트를 저장할 수 있습니다.",
    saveCommandMessage:
      "지금까지 논의한 모든 내용을 바탕으로 이 사용자 정의 에이전트를 지금 저장해 주세요. 이것을 저장에 대한 명시적 확인으로 간주하세요. 일부 세부 정보가 누락되어 있다면 합리적으로 가정하여 간결한 SOUL.md 초안을 영어로 작성하고, 추가 확인 없이 즉시 setup_agent를 호출하세요.",
    agentCreatedPendingRefresh:
      "에이전트는 생성되었지만 DeerFlow가 아직 불러올 수 없습니다. 잠시 후 이 페이지를 새로고침해 주세요.",
    more: "추가 작업",
    agentCreated: "에이전트가 생성되었습니다!",
    startChatting: "채팅 시작",
    backToGallery: "갤러리로 돌아가기",
  },

  // Breadcrumb
  breadcrumb: {
    workspace: "워크스페이스",
    chats: "채팅",
  },

  // Workspace
  workspace: {
    officialWebsite: "DeerFlow 공식 웹사이트",
    githubTooltip: "GitHub의 DeerFlow",
    settingsAndMore: "설정 및 더보기",
    visitGithub: "GitHub의 DeerFlow",
    reportIssue: "이슈 신고",
    contactUs: "문의하기",
    about: "DeerFlow 정보",
    logout: "로그아웃",
  },

  // Conversation
  conversation: {
    noMessages: "메시지가 아직 없습니다",
    startConversation: "대화를 시작하면 여기에 메시지가 표시됩니다",
  },

  // Chats
  chats: {
    searchChats: "채팅 검색",
  },

  // Page titles (document title)
  pages: {
    appName: "DeerFlow",
    chats: "채팅",
    newChat: "새 채팅",
    untitled: "제목 없음",
  },

  // Tool calls
  toolCalls: {
    moreSteps: (count: number) => `${count}단계 더보기`,
    lessSteps: "단계 접기",
    executeCommand: "명령 실행",
    presentFiles: "파일 표시",
    needYourHelp: "도움이 필요합니다",
    useTool: (toolName: string) => `"${toolName}" 도구 사용`,
    searchFor: (query: string) => `"${query}" 검색`,
    searchForRelatedInfo: "관련 정보 검색",
    searchForRelatedImages: "관련 이미지 검색",
    searchForRelatedImagesFor: (query: string) =>
      `"${query}"에 대한 관련 이미지 검색`,
    searchOnWebFor: (query: string) => `웹에서 "${query}" 검색`,
    viewWebPage: "웹페이지 보기",
    listFolder: "폴더 목록 보기",
    readFile: "파일 읽기",
    writeFile: "파일 쓰기",
    clickToViewContent: "클릭하여 파일 내용 보기",
    writeTodos: "할 일 목록 업데이트",
    skillInstallTooltip: "스킬을 설치하여 DeerFlow에서 사용할 수 있게 합니다",
  },

  // Uploads
  uploads: {
    uploading: "업로드 중...",
    uploadingFiles: "파일을 업로드하는 중입니다. 잠시만 기다려 주세요...",
  },

  subtasks: {
    subtask: "서브태스크",
    executing: (count: number) =>
      count === 1 ? "서브태스크 실행 중" : `${count}개의 서브태스크 병렬 실행 중`,
    in_progress: "서브태스크 실행 중",
    completed: "서브태스크 완료",
    failed: "서브태스크 실패",
  },

  // Token Usage
  tokenUsage: {
    title: "토큰 사용량",
    label: "토큰",
    input: "입력",
    output: "출력",
    total: "합계",
    view: "표시",
    unavailable:
      "아직 토큰 사용량 정보가 없습니다. 모델 응답이 성공적으로 완료되고 제공자가 usage_metadata를 반환한 후에만 표시됩니다.",
    unavailableShort: "사용량 정보 없음",
    note: "헤더 합계는 저장된 스레드 사용량에 스트리밍 중인 실시간 사용량을 더한 값입니다. 턴별·디버그 사용량은 현재 표시된 메시지에만 적용됩니다. 제공자 청구 페이지와 다를 수 있습니다.",
    presets: {
      off: "끔",
      summary: "요약",
      perTurn: "턴별",
      debug: "디버그",
    },
    presetDescriptions: {
      off: "헤더와 대화에서 토큰 사용량을 숨깁니다.",
      summary: "헤더에 현재 대화 합계만 표시합니다.",
      perTurn:
        "헤더 합계와 각 어시스턴트 턴별 토큰 요약을 표시합니다.",
      debug: "헤더 합계와 단계별 토큰 디버깅 정보를 표시합니다.",
    },
    finalAnswer: "최종 답변",
    stepTotal: "단계 합계",
    sharedAttribution: "이 단계의 여러 작업에서 공유됨",
    subagent: (description: string) => `서브에이전트: ${description}`,
    startTodo: (content: string) => `할 일 시작: ${content}`,
    completeTodo: (content: string) => `할 일 완료: ${content}`,
    updateTodo: (content: string) => `할 일 업데이트: ${content}`,
    removeTodo: (content: string) => `할 일 제거: ${content}`,
  },

  // Shortcuts
  shortcuts: {
    searchActions: "작업 검색...",
    noResults: "결과를 찾을 수 없습니다.",
    actions: "작업",
    keyboardShortcuts: "키보드 단축키",
    keyboardShortcutsDescription:
      "키보드 단축키로 DeerFlow를 더 빠르게 탐색하세요.",
    openCommandPalette: "명령 팔레트 열기",
    toggleSidebar: "사이드바 토글",
  },

  // Settings
  settings: {
    title: "설정",
    description: "DeerFlow의 모습과 동작을 사용자에 맞게 조정합니다.",
    sections: {
      account: "계정",
      appearance: "화면",
      memory: "메모리",
      tools: "도구",
      skills: "스킬",
      notification: "알림",
      about: "정보",
    },
    memory: {
      title: "메모리",
      description:
        "DeerFlow는 대화에서 자동으로 학습합니다. 이 메모리는 DeerFlow가 사용자를 더 잘 이해하고 맞춤형 경험을 제공하는 데 사용됩니다.",
      empty: "표시할 메모리 데이터가 없습니다.",
      rawJson: "원본 JSON",
      exportButton: "메모리 내보내기",
      exportSuccess: "메모리를 내보냈습니다",
      importButton: "메모리 가져오기",
      importConfirmTitle: "메모리를 가져올까요?",
      importConfirmDescription:
        "선택한 JSON 백업으로 현재 메모리를 덮어씁니다.",
      importFileLabel: "선택된 파일",
      importInvalidFile:
        "선택한 메모리 파일을 읽지 못했습니다. 올바른 JSON 내보내기 파일을 선택하세요.",
      importSuccess: "메모리를 가져왔습니다",
      manualFactSource: "수동",
      addFact: "사실 추가",
      addFactTitle: "메모리 사실 추가",
      editFactTitle: "메모리 사실 편집",
      addFactSuccess: "사실이 생성되었습니다",
      editFactSuccess: "사실이 업데이트되었습니다",
      clearAll: "모든 메모리 지우기",
      clearAllConfirmTitle: "모든 메모리를 지울까요?",
      clearAllConfirmDescription:
        "저장된 모든 요약과 사실이 삭제됩니다. 이 작업은 되돌릴 수 없습니다.",
      clearAllSuccess: "모든 메모리가 삭제되었습니다",
      factDeleteConfirmTitle: "이 사실을 삭제할까요?",
      factDeleteConfirmDescription:
        "이 사실은 메모리에서 즉시 제거됩니다. 이 작업은 되돌릴 수 없습니다.",
      factDeleteSuccess: "사실이 삭제되었습니다",
      factContentLabel: "내용",
      factCategoryLabel: "카테고리",
      factConfidenceLabel: "신뢰도",
      factContentPlaceholder: "저장하려는 메모리 사실을 입력하세요",
      factCategoryPlaceholder: "context",
      factConfidenceHint: "0에서 1 사이의 숫자를 사용하세요.",
      factSave: "사실 저장",
      factValidationContent: "사실 내용은 비어 있을 수 없습니다.",
      factValidationConfidence:
        "신뢰도는 0과 1 사이의 숫자여야 합니다.",
      noFacts: "저장된 사실이 아직 없습니다.",
      summaryReadOnly:
        "요약 섹션은 현재 읽기 전용입니다. 지금은 개별 사실을 추가·편집·삭제하거나 전체 메모리를 지울 수 있습니다.",
      memoryFullyEmpty: "아직 저장된 메모리가 없습니다.",
      factPreviewLabel: "삭제할 사실",
      searchPlaceholder: "메모리 검색",
      filterAll: "전체",
      filterFacts: "사실",
      filterSummaries: "요약",
      noMatches: "일치하는 메모리를 찾을 수 없습니다.",
      markdown: {
        overview: "개요",
        userContext: "사용자 컨텍스트",
        work: "업무",
        personal: "개인",
        topOfMind: "최근 관심사",
        historyBackground: "이력",
        recentMonths: "최근 몇 개월",
        earlierContext: "이전 컨텍스트",
        longTermBackground: "장기 배경",
        updatedAt: "업데이트 시각",
        facts: "사실",
        empty: "(비어 있음)",
        table: {
          category: "카테고리",
          confidence: "신뢰도",
          confidenceLevel: {
            veryHigh: "매우 높음",
            high: "높음",
            normal: "보통",
            unknown: "알 수 없음",
          },
          content: "내용",
          source: "출처",
          createdAt: "생성 일시",
          view: "보기",
        },
      },
    },
    appearance: {
      themeTitle: "테마",
      themeDescription:
        "인터페이스가 기기 설정을 따를지, 고정 테마를 사용할지 선택하세요.",
      system: "시스템",
      light: "라이트",
      dark: "다크",
      systemDescription: "운영체제 설정을 자동으로 따릅니다.",
      lightDescription: "낮 시간에 적합한 밝은 색상과 높은 대비.",
      darkDescription: "눈부심을 줄여 집중에 좋은 어두운 색상.",
      languageTitle: "언어",
      languageDescription: "언어를 전환합니다.",
    },
    tools: {
      title: "도구",
      description: "MCP 도구의 설정과 활성화 상태를 관리합니다.",
    },
    skills: {
      title: "에이전트 스킬",
      description: "에이전트 스킬의 설정과 활성화 상태를 관리합니다.",
      createSkill: "스킬 만들기",
      emptyTitle: "에이전트 스킬이 아직 없습니다",
      emptyDescription:
        "에이전트 스킬 폴더를 DeerFlow 루트의 `/skills/custom` 폴더 아래에 두세요.",
      emptyButton: "첫 번째 스킬 만들기",
    },
    notification: {
      title: "알림",
      description:
        "DeerFlow는 창이 활성화되어 있지 않을 때만 완료 알림을 보냅니다. 장시간 실행되는 작업에서 다른 일을 하다가 완료 시 알림을 받기에 특히 유용합니다.",
      requestPermission: "알림 권한 요청",
      deniedHint:
        "알림 권한이 거부되었습니다. 브라우저의 사이트 설정에서 권한을 활성화하면 완료 알림을 받을 수 있습니다.",
      testButton: "테스트 알림 보내기",
      testTitle: "DeerFlow",
      testBody: "테스트 알림입니다.",
      notSupported: "사용 중인 브라우저는 알림을 지원하지 않습니다.",
      disableNotification: "알림 비활성화",
    },
    account: {
      profileTitle: "프로필",
      email: "이메일",
      role: "역할",
      changePasswordTitle: "비밀번호 변경",
      changePasswordDescription: "계정 비밀번호를 업데이트합니다.",
      currentPassword: "현재 비밀번호",
      newPassword: "새 비밀번호",
      confirmNewPassword: "새 비밀번호 확인",
      passwordMismatch: "새 비밀번호가 일치하지 않습니다",
      passwordTooShort: "비밀번호는 최소 8자 이상이어야 합니다",
      passwordChangedSuccess: "비밀번호가 변경되었습니다",
      networkError: "네트워크 오류입니다. 다시 시도해 주세요.",
      updating: "업데이트 중...",
      updatePassword: "비밀번호 업데이트",
      signOut: "로그아웃",
    },
    acknowledge: {
      emptyTitle: "감사의 말",
      emptyDescription: "크레딧과 감사의 말이 여기에 표시됩니다.",
    },
  },
};
