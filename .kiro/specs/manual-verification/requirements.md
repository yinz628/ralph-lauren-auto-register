# Requirements Document

## Introduction

本规范定义了在 Ralph Lauren 自动注册系统中引入人工验证机制的需求。当 PerimeterX 防机器人系统出现验证挑战时，系统将暂停自动化流程，等待用户手动完成验证，验证成功后自动继续执行后续流程。

## Glossary

- **System**: Ralph Lauren 自动注册系统
- **PerimeterX**: 网站使用的防机器人检测系统
- **Manual_Verification**: 人工验证模式，需要用户手动点击完成验证
- **Verification_Challenge**: PerimeterX 显示的验证挑战界面
- **Auto_Redirect**: 验证成功后网页自动跳转到目标页面
- **Verification_Timeout**: 等待人工验证的最大时间限制

## Requirements

### Requirement 1: PerimeterX 挑战检测

**User Story:** As a user, I want the system to detect when PerimeterX challenge appears, so that I can be notified to perform manual verification.

#### Acceptance Criteria

1. WHEN the System submits registration form THEN the System SHALL check for PerimeterX challenge elements on the page
2. WHEN checking for challenges THEN the System SHALL look for common PerimeterX selectors including captcha containers, challenge modals, and iframe elements
3. WHEN a PerimeterX challenge is detected THEN the System SHALL identify the challenge type (press-and-hold, checkbox, slider, etc.)
4. WHEN no challenge is detected within 3 seconds THEN the System SHALL proceed with normal flow monitoring

### Requirement 2: 人工验证模式切换

**User Story:** As a user, I want the system to pause automation and wait for my manual input when PerimeterX challenge appears, so that I can complete the verification myself.

#### Acceptance Criteria

1. WHEN a PerimeterX challenge is detected THEN the System SHALL pause all automated interactions
2. WHEN entering manual verification mode THEN the System SHALL display a clear notification message to the user
3. WHEN in manual verification mode THEN the System SHALL keep the browser window visible (non-headless mode)
4. WHEN displaying notification THEN the System SHALL include instructions on what the user needs to do
5. WHEN in manual verification mode THEN the System SHALL log the event with timestamp and challenge type

### Requirement 3: 验证完成监控

**User Story:** As a user, I want the system to automatically detect when I complete the verification, so that automation can resume without manual intervention.

#### Acceptance Criteria

1. WHEN waiting for manual verification THEN the System SHALL continuously monitor for page navigation events
2. WHEN monitoring navigation THEN the System SHALL check if the current URL matches the expected success pattern
3. WHEN monitoring navigation THEN the System SHALL check if PerimeterX challenge elements disappear from the page
4. WHEN the page navigates to the success URL THEN the System SHALL detect verification completion
5. WHEN PerimeterX challenge elements are no longer present THEN the System SHALL consider verification potentially complete

### Requirement 4: 超时处理

**User Story:** As a user, I want the system to handle cases where I cannot complete verification in time, so that the system doesn't hang indefinitely.

#### Acceptance Criteria

1. WHEN entering manual verification mode THEN the System SHALL start a timeout timer with configurable duration
2. WHEN the timeout duration is reached THEN the System SHALL log a timeout event
3. WHEN verification times out THEN the System SHALL mark the current iteration as failed
4. WHEN verification times out THEN the System SHALL clean up browser resources and proceed to next iteration
5. WHEN timeout occurs THEN the System SHALL provide clear error message indicating manual verification timeout

### Requirement 5: 验证成功后流程恢复

**User Story:** As a user, I want the system to automatically continue the registration process after I complete verification, so that I don't need to manually trigger the next steps.

#### Acceptance Criteria

1. WHEN verification is detected as complete THEN the System SHALL log a success event
2. WHEN verification succeeds THEN the System SHALL resume automated flow from the next step
3. WHEN resuming flow THEN the System SHALL verify the current page state matches expected state
4. WHEN on profile page after verification THEN the System SHALL proceed with profile update flow
5. WHEN verification completes THEN the System SHALL continue monitoring for subsequent challenges

### Requirement 6: 配置管理

**User Story:** As a user, I want to configure manual verification settings, so that I can adjust timeout and behavior according to my needs.

#### Acceptance Criteria

1. WHEN the System loads configuration THEN the System SHALL read manual verification timeout setting (default 120 seconds)
2. WHEN the System loads configuration THEN the System SHALL read notification display preferences
3. WHEN the System starts THEN the System SHALL always use manual verification mode (no automatic solving option)

### Requirement 7: 日志和监控

**User Story:** As a user, I want detailed logs of verification events, so that I can track and debug verification issues.

#### Acceptance Criteria

1. WHEN a challenge is detected THEN the System SHALL log challenge type, timestamp, and page URL
2. WHEN entering manual verification mode THEN the System SHALL log entry timestamp and timeout duration
3. WHEN verification completes THEN the System SHALL log completion timestamp and total duration
4. WHEN verification times out THEN the System SHALL log timeout event with duration
5. WHEN verification fails THEN the System SHALL log failure reason and any error details

### Requirement 8: 多次验证支持

**User Story:** As a user, I want the system to handle multiple verification challenges in a single registration flow, so that registration can complete even with repeated challenges.

#### Acceptance Criteria

1. WHEN a verification challenge appears after profile update THEN the System SHALL handle it the same way as registration verification
2. WHEN multiple challenges appear in sequence THEN the System SHALL handle each one independently
3. WHEN the System encounters more than 3 challenges in one iteration THEN the System SHALL mark the iteration as failed
4. WHEN handling multiple challenges THEN the System SHALL maintain state between challenges


### Requirement 9: 移除自动化验证

**User Story:** As a user, I want to remove all automatic PerimeterX challenge solving code, so that the system only relies on manual verification.

#### Acceptance Criteria

1. WHEN the System detects a PerimeterX challenge THEN the System SHALL NOT attempt any automatic solving methods
2. WHEN refactoring code THEN the System SHALL remove all automatic press-and-hold solving logic
3. WHEN refactoring code THEN the System SHALL remove all automatic mouse movement and clicking for challenges
4. WHEN refactoring code THEN the System SHALL remove the `_solve_px_press_hold` method from Registration class
5. WHEN refactoring code THEN the System SHALL remove the `_solve_px_press_hold` method from BrowserController class
6. WHEN a challenge is detected THEN the System SHALL immediately enter manual verification mode without attempting automatic solving
