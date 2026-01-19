# Requirements Document

## Introduction

本系统是一个 Ralph Lauren 网站自动注册工具，通过代理IP从API获取用户数据，自动完成账户注册和个人信息更新流程。系统需要绕过 PerimeterX 防机器人系统，并支持批量迭代注册。

## Glossary

- **System**: Ralph Lauren 自动注册系统
- **API**: 用户数据接口 (http://1.94.38.63:5000/)
- **Proxy**: 代理服务器，用于隐藏真实IP
- **PerimeterX**: 网站使用的防机器人检测系统
- **Registration Page**: Ralph Lauren 注册页面 (https://www.ralphlauren.com/register)
- **Profile Page**: Ralph Lauren 个人资料页面 (https://www.ralphlauren.com/profile)

## Requirements

### Requirement 1: 数据准备模块

**User Story:** As a user, I want to fetch registration data from an API, so that I can use it for automated registration.

#### Acceptance Criteria

1. WHEN the System starts THEN the System SHALL fetch user data (email, first_name, last_name, password, phone_number) from the configured API endpoint
2. WHEN the System receives API response THEN the System SHALL parse JSON data and extract required fields
3. WHEN the System initializes THEN the System SHALL generate a random day between 1 and 28 based on configured month
4. WHEN the System makes API requests THEN the System SHALL bypass proxy settings for the data API

### Requirement 2: 代理管理模块

**User Story:** As a user, I want to use rotating proxies from US region, so that I can avoid IP-based blocking.

#### Acceptance Criteria

1. WHEN the System needs a proxy THEN the System SHALL generate a proxy URL using configured IP and a random port between 50000 and 50020
2. WHEN a proxy is generated THEN the System SHALL validate the proxy by checking response from http://ip-api.com/json/
3. WHEN validating a proxy THEN the System SHALL measure connection latency
4. WHEN validating a proxy THEN the System SHALL verify the proxy location is in the US region
5. IF a proxy fails validation THEN the System SHALL retry with a different random port

### Requirement 3: 浏览器自动化模块

**User Story:** As a user, I want the browser to be configured to bypass anti-bot detection, so that registration can proceed without being blocked.

#### Acceptance Criteria

1. WHEN the browser launches THEN the System SHALL configure settings to evade PerimeterX detection
2. WHEN the browser is configured THEN the System SHALL use the validated US proxy
3. WHEN the browser navigates to a page THEN the System SHALL wait for page load completion before interacting

### Requirement 4: 注册流程模块

**User Story:** As a user, I want to automatically register accounts on Ralph Lauren website, so that I can create accounts efficiently.

#### Acceptance Criteria

1. WHEN registration starts THEN the System SHALL navigate to https://www.ralphlauren.com/register and refresh once
2. WHEN the registration page loads THEN the System SHALL locate element with id="dwfrm_profile_customer_email" and input email
3. WHEN filling password THEN the System SHALL locate element with id pattern "dwfrm_profile_login_password_*" (12 random digits suffix) and input password
4. WHEN confirming password THEN the System SHALL locate element with id pattern "dwfrm_profile_login_passwordconfirm_*" (12 random digits suffix) and input password
5. WHEN filling name THEN the System SHALL locate element with id="dwfrm_profile_customer_firstname" and input first_name
6. WHEN filling name THEN the System SHALL locate element with id="dwfrm_profile_customer_lastname" and input last_name
7. WHEN form is filled THEN the System SHALL click button with name="dwfrm_profile_confirm"
8. WHEN submit button is clicked THEN the System SHALL monitor for navigation to https://www.ralphlauren.com/pplp/account?fromAccountLogin=true to determine registration success
9. IF registration succeeds THEN the System SHALL navigate to https://www.ralphlauren.com/profile

### Requirement 5: 个人资料更新模块

**User Story:** As a user, I want to update profile information after registration, so that the account has complete birthday and phone data.

#### Acceptance Criteria

1. WHEN profile page loads THEN the System SHALL locate dropdown with id="dwfrm_profile_customer_month" and select configured month (English month name)
2. WHEN selecting birthday THEN the System SHALL locate dropdown with id="dwfrm_profile_customer_day" and select generated day
3. WHEN filling phone THEN the System SHALL locate element with id="dwfrm_profile_customer_phone" and input phone_number
4. WHEN filling mobile THEN the System SHALL locate element with id="dwfrm_profile_customer_phoneMobile" and input phone_number
5. WHEN profile form is filled THEN the System SHALL click button with name="dwfrm_profile_confirm"
6. WHEN profile is submitted THEN the System SHALL monitor for HTTP 302 response from https://www.ralphlauren.com/on/demandware.store/Sites-RalphLauren_US-Site/en_US/Account-EditForm to confirm success

### Requirement 6: 数据持久化模块

**User Story:** As a user, I want to save successful registration data, so that I can track created accounts.

#### Acceptance Criteria

1. WHEN registration and profile update succeed THEN the System SHALL save email, password, and birthday to a file
2. WHEN saving data THEN the System SHALL append to existing records without overwriting

### Requirement 7: 配置管理模块

**User Story:** As a user, I want to configure system parameters in a config file, so that I can easily adjust settings.

#### Acceptance Criteria

1. WHEN the System loads THEN the System SHALL read API endpoint from config.py
2. WHEN the System loads THEN the System SHALL read proxy IP and port range from config.py
3. WHEN the System loads THEN the System SHALL read iteration count and interval from config.py
4. WHEN the System loads THEN the System SHALL read month setting from config.py

### Requirement 8: 迭代执行模块

**User Story:** As a user, I want to run multiple registration iterations with delays, so that I can create multiple accounts safely.

#### Acceptance Criteria

1. WHEN running in batch mode THEN the System SHALL execute registration flow for configured iteration count
2. WHEN completing one iteration THEN the System SHALL wait for configured interval before next iteration
3. IF an iteration fails THEN the System SHALL log the error and continue to next iteration
