# 코드 품질 4가지 기준

좋은 프론트엔드 코드는 **변경하기 쉬운** 코드입니다. 새로운 요구사항이 들어왔을 때 기존 코드를 수정하고 배포하기 수월한 코드가 좋은 코드입니다. 다음 4가지 기준으로 판단합니다.

## 1. 가독성 (Readability)

코드가 읽기 쉬운 정도입니다. 코드가 변경하기 쉬우려면 먼저 코드가 어떤 동작을 하는지 이해할 수 있어야 합니다. 읽기 좋은 코드는 읽는 사람이 한 번에 머릿속에서 고려하는 맥락이 적고, 위에서 아래로 자연스럽게 이어집니다.

### 맥락 줄이기

**A. 같이 실행되지 않는 코드 분리하기**

동시에 실행되지 않는 코드가 하나의 함수/컴포넌트에 있으면 동작 파악이 어렵고 분기가 많아집니다.

```tsx
// ❌ 분기가 뒤섞인 코드
function SubmitButton() {
  const isViewer = useRole() === "viewer";

  useEffect(() => {
    if (isViewer) { return; }
    showButtonAnimation();
  }, [isViewer]);

  return isViewer
    ? <TextButton disabled>Submit</TextButton>
    : <Button type="submit">Submit</Button>;
}

// ✅ 권한별로 컴포넌트 분리
function SubmitButton() {
  const isViewer = useRole() === "viewer";
  return isViewer ? <ViewerSubmitButton /> : <AdminSubmitButton />;
}

function ViewerSubmitButton() {
  return <TextButton disabled>Submit</TextButton>;
}

function AdminSubmitButton() {
  useEffect(() => { showButtonAnimation(); }, []);
  return <Button type="submit">Submit</Button>;
}
```

**B. 구현 상세 추상화하기**

한 사람이 한 번에 고려할 수 있는 맥락은 제한적입니다. 불필요한 맥락을 Wrapper 컴포넌트나 HOC로 추상화하면 가독성이 높아집니다.

```tsx
// ❌ 로그인 체크 로직이 노출됨
function LoginStartPage() {
  useCheckLogin({
    onChecked: (status) => {
      if (status === "LOGGED_IN") { location.href = "/home"; }
    }
  });
  /* ... 로그인 관련 로직 ... */
  return <>{/* ... 로그인 관련 컴포넌트 ... */}</>;
}

// ✅ AuthGuard로 분리
function App() {
  return (
    <AuthGuard>
      <LoginStartPage />
    </AuthGuard>
  );
}

function AuthGuard({ children }) {
  const status = useCheckLoginStatus();
  useEffect(() => {
    if (status === "LOGGED_IN") { location.href = "/home"; }
  }, [status]);
  return status !== "LOGGED_IN" ? children : null;
}
```

**C. 로직 종류에 따라 합쳐진 함수 쪼개기**

쿼리 파라미터, 상태, API 호출 등 로직의 종류에 따라 함수를 만들지 마세요. 한 번에 다루는 맥락의 종류가 많아져 이해하고 수정하기 어려워집니다. 대신 도메인/기능 단위로 쪼개세요.

### 이름 붙이기

**A. 복잡한 조건에 이름 붙이기**

복잡한 조건식이 이름 없이 사용되면 의도 파악이 어렵습니다. 조건에 명시적 이름을 붙이면 한 번에 고려할 맥락이 줄어듭니다.

```typescript
// ❌ 복잡한 조건이 익명 함수 안에 중첩
const result = products.filter((product) =>
  product.categories.some(
    (category) =>
      category.id === targetCategory.id &&
      product.prices.some((price) => price >= minPrice && price <= maxPrice)
  )
);

// ✅ 조건에 이름 붙이기
const matchedProducts = products.filter((product) => {
  return product.categories.some((category) => {
    const isSameCategory = category.id === targetCategory.id;
    const isPriceInRange = product.prices.some(
      (price) => price >= minPrice && price <= maxPrice
    );
    return isSameCategory && isPriceInRange;
  });
});
```

**B. 매직 넘버에 이름 붙이기**

의미를 알 수 없는 숫자 값을 그대로 사용하면, 작성자가 아니면 의도를 알 수 없습니다.

```typescript
// ❌ 300이 어떤 의미인지 알 수 없음
async function onLikeClick() {
  await postLike(url);
  await delay(300);
  await refetchPostLike();
}

// ✅ 상수로 의도 명확화
const ANIMATION_DELAY_MS = 300;

async function onLikeClick() {
  await postLike(url);
  await delay(ANIMATION_DELAY_MS);
  await refetchPostLike();
}
```

### 위에서 아래로 읽히게 하기

**A. 시점 이동 줄이기**

코드를 위아래로 왔다갔다 읽거나 여러 파일을 넘나들면 파악에 시간이 오래 걸립니다. 위에서 아래로만 읽어도 이해할 수 있도록 작성하세요.

```tsx
// ❌ policy → getPolicyByRole → POLICY_SET 오가며 3번 시점 이동
function Page() {
  const user = useUser();
  const policy = getPolicyByRole(user.role);
  return (
    <div>
      <Button disabled={!policy.canInvite}>Invite</Button>
      <Button disabled={!policy.canView}>View</Button>
    </div>
  );
}

// ✅ 조건을 펼쳐서 한눈에 파악
function Page() {
  const user = useUser();

  switch (user.role) {
    case "admin":
      return (
        <div>
          <Button disabled={false}>Invite</Button>
          <Button disabled={false}>View</Button>
        </div>
      );
    case "viewer":
      return (
        <div>
          <Button disabled={true}>Invite</Button>
          <Button disabled={false}>View</Button>
        </div>
      );
    default:
      return null;
  }
}
```

**B. 삼항 연산자 단순하게 하기**

중첩된 삼항 연산자는 조건 구조가 명확히 보이지 않습니다. if문으로 풀어쓰면 조건이 명확해집니다.

```typescript
// ❌ 중첩 삼항 연산자
const status =
  A조건 && B조건 ? "BOTH" : A조건 || B조건 ? (A조건 ? "A" : "B") : "NONE";

// ✅ if문으로 풀어쓰기
const status = (() => {
  if (A조건 && B조건) return "BOTH";
  if (A조건) return "A";
  if (B조건) return "B";
  return "NONE";
})();
```

## 2. 예측 가능성 (Predictability)

함께 협업하는 동료들이 함수나 컴포넌트의 동작을 얼마나 예측할 수 있는지를 말합니다. 예측 가능성이 높은 코드는 일관적인 규칙을 따르고, 함수나 컴포넌트의 이름과 파라미터, 반환 값만 보고도 어떤 동작을 하는지 알 수 있습니다.

### A. 이름 겹치지 않게 관리하기

같은 이름을 가진 함수가 다른 동작을 하면 예측 가능성이 낮아집니다. 라이브러리 함수명과 구분되는 명확한 이름을 사용하세요.

```typescript
// ❌ http.get이 토큰을 추가하는지 호출부에서 알 수 없음
export const http = {
  async get(url: string) {
    const token = await fetchToken();
    return httpLibrary.get(url, { headers: { Authorization: `Bearer ${token}` } });
  }
};

// ✅ 이름으로 동작을 명확히 전달
export const httpService = {
  async getWithAuth(url: string) {
    const token = await fetchToken();
    return httpLibrary.get(url, { headers: { Authorization: `Bearer ${token}` } });
  }
};
```

### B. 같은 종류의 함수는 반환 타입 통일하기

API 호출 Hook끼리 반환 타입이 다르면, 사용할 때마다 반환 타입을 확인해야 합니다. 같은 종류의 함수는 일관된 반환 타입을 유지하세요.

```typescript
// ❌ useUser는 Query 객체 반환, useServerTime은 데이터만 반환
function useUser() {
  const query = useQuery({ queryKey: ["user"], queryFn: fetchUser });
  return query;
}

function useServerTime() {
  const query = useQuery({ queryKey: ["serverTime"], queryFn: fetchServerTime });
  return query.data; // 불일치!
}

// ✅ 일관되게 Query 객체 반환
function useServerTime() {
  const query = useQuery({ queryKey: ["serverTime"], queryFn: fetchServerTime });
  return query;
}
```

### C. 숨은 로직 드러내기

함수의 이름, 파라미터, 반환 값에 드러나지 않는 숨은 로직이 있으면 동료가 동작을 예측하기 어렵습니다. 함수에 예측 가능한 로직만 남기고 부수 효과는 별도로 분리하세요.

```typescript
// ❌ fetchBalance에 숨은 로깅이 있음
async function fetchBalance(): Promise<number> {
  const balance = await http.get<number>("...");
  logging.log("balance_fetched"); // 호출부에서 예측 불가
  return balance;
}

// ✅ 부수 효과는 호출부로 이동
async function fetchBalance(): Promise<number> {
  const balance = await http.get<number>("...");
  return balance;
}

// 호출부에서 로깅
<Button onClick={async () => {
  const balance = await fetchBalance();
  logging.log("balance_fetched");
  await syncBalance(balance);
}}>계좌 잔액 갱신하기</Button>
```

## 3. 응집도 (Cohesion)

수정되어야 할 코드가 항상 같이 수정되는지를 말합니다. 응집도가 높은 코드는 코드의 한 부분을 수정해도 의도치 않게 다른 부분에서 오류가 발생하지 않습니다. 함께 수정되어야 할 부분이 반드시 함께 수정되도록 구조적으로 뒷받침되기 때문입니다.

### A. 함께 수정되는 파일을 같은 디렉토리에 두기

파일을 종류별(components, hooks, utils 등)로만 나누면 의존 관계를 파악하기 어렵고, 삭제 시 연관 코드가 남을 수 있습니다. 함께 수정되는 파일은 도메인 단위 디렉토리에 모으세요.

```text
# ❌ 종류별 분류 — 의존 관계 파악 어려움
└─ src
   ├─ components/
   ├─ hooks/
   └─ utils/

# ✅ 도메인 단위 분류 — 의존 관계 명확
└─ src
   ├─ components/        # 전체 프로젝트 공통
   ├─ hooks/
   └─ domains/
      ├─ Domain1/        # 도메인1 전용
      │   ├─ components/
      │   ├─ hooks/
      │   └─ utils/
      └─ Domain2/        # 도메인2 전용
          ├─ components/
          ├─ hooks/
          └─ utils/
```

### B. 매직 넘버 없애기 (응집도 관점)

같이 수정되어야 할 숫자 값이 상수로 분리되지 않으면, 애니메이션 시간이 바뀌었을 때 한쪽만 수정되어 조용히 서비스가 깨질 수 있습니다. (가독성 관점과 동일한 예시이지만, 응집도 측면에서는 "함께 수정되어야 할 값이 한 곳에 모여 있는가"가 핵심입니다.)

### C. 폼의 응집도 생각하기

폼 설계 시 두 가지 응집 방식을 상황에 맞게 선택하세요.

- **필드 단위 응집**: 각 필드가 독립 검증 로직을 가짐. 특정 필드 유지보수가 쉬움.
- **폼 전체 단위 응집**: 모든 필드 검증이 폼에 종속. 폼 전체 흐름 파악이 쉬움. 필드 간 결합도가 높아 재사용성은 떨어질 수 있음.

## 4. 결합도 (Coupling)

코드를 수정했을 때의 영향 범위를 말합니다. 코드를 수정했을 때 영향 범위가 적어서, 변경에 따른 범위를 예측할 수 있는 코드가 수정하기 쉬운 코드입니다.

### A. 책임을 하나씩 관리하기

하나의 Hook이 모든 쿼리 파라미터를 관리하면 수정 시 영향 범위가 급격히 확장됩니다. 쿼리 파라미터별로 별도의 Hook을 작성하여 결합도를 낮추세요.

```typescript
// ❌ 모든 쿼리 파라미터를 하나의 Hook에서 관리
function usePageState() {
  const [query, setQuery] = useQueryParams({
    cardId: NumberParam, statementId: NumberParam,
    dateFrom: DateParam, dateTo: DateParam, statusList: ArrayParam
  });
  // ... 모든 값과 setter 반환
}

// ✅ 파라미터별 개별 Hook
function useCardId() { /* ... */ }
function useStatementId() { /* ... */ }
function useDateRange() { /* ... */ }
```

### B. 중복 코드 허용하기

여러 페이지의 반복 코드를 공통 Hook으로 만들면 응집도는 높아지지만, 페이지마다 요구사항이 달라지면 공통 코드가 복잡해지고 수정 시 모든 페이지에 영향을 줍니다. 페이지마다 동작이 달라질 여지가 있다면 공통화 대신 중복을 허용하세요.

```typescript
// ❌ 여러 페이지의 미묘하게 다른 로직을 하나의 Hook으로 강제 통합
export const useOpenMaintenanceBottomSheet = () => {
  const maintenanceBottomSheet = useMaintenanceBottomSheet();
  const logger = useLogger();
  return async (maintainingInfo: TelecomMaintenanceInfo) => {
    logger.log("점검 바텀시트 열림");
    const result = await maintenanceBottomSheet.open(maintainingInfo);
    if (result) { logger.log("점검 바텀시트 알림받기 클릭"); }
    closeView();
  };
};

// ✅ 각 페이지에서 필요한 만큼 직접 작성 (중복 허용)
// 페이지 A: 로깅 + 바텀시트 + 화면 닫기
// 페이지 B: 로깅 없이 바텀시트만
// 페이지 C: 커스텀 텍스트 + 바텀시트
```

### C. Props Drilling 지우기

부모→자식으로 prop을 그대로 전달하는 Props Drilling이 발생하면, prop 변경 시 참조하는 모든 컴포넌트를 수정해야 합니다. 조합(Composition) 패턴이나 Context를 활용해 결합도를 낮추세요.

```tsx
// ❌ props가 여러 레벨로 drilling됨
function ItemEditModal({ open, items, recommendedItems, onConfirm, onClose }) {
  return (
    <Modal open={open} onClose={onClose}>
      <ItemEditBody
        items={items} keyword={keyword} onKeywordChange={setKeyword}
        recommendedItems={recommendedItems} onConfirm={onConfirm} onClose={onClose}
      />
    </Modal>
  );
}

// ✅ 조합 패턴으로 불필요한 prop 전달 제거
function ItemEditModal({ open, onConfirm, onClose }) {
  return (
    <Modal open={open} onClose={onClose}>
      <ItemEditHeader onClose={onClose} />
      <ItemEditList onConfirm={onConfirm} />
    </Modal>
  );
}
```

## 기준 간 상충

아쉽게도 이 4가지 기준을 모두 한꺼번에 충족하기는 어렵습니다. 기준 사이에는 상충이 존재합니다.

- **응집도 vs 가독성**: 응집도를 높이기 위해 공통화·추상화하면 코드가 한 차례 추상화되어 가독성이 떨어집니다. 함께 수정되지 않으면 오류가 발생할 수 있는 경우에는 응집도를 우선하세요. 위험성이 높지 않은 경우에는 가독성을 우선하여 코드 중복을 허용하세요.
- **결합도 vs 응집도**: 중복 코드를 허용하면 영향 범위를 줄일 수 있어 결합도는 낮아지지만, 한쪽을 수정할 때 다른 쪽을 실수로 수정하지 못할 수 있어 응집도는 떨어집니다.

프론트엔드 개발자는 현재 직면한 상황을 바탕으로, 장기적으로 코드가 수정하기 쉽게 하기 위해 어떤 가치를 우선해야 하는지 고민해야 합니다.
