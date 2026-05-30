; VideoSum Inno Setup 安装脚本
; 需要安装 Inno Setup: https://jrsoftware.org/isinfo.php

#define MyAppName "VideoSum"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "VideoSum Team"
#define MyAppURL "https://github.com/qquieen/videosum"
#define MyAppExeName "VideoSum.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer
OutputBaseFilename=VideoSum_Setup_{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 主程序文件
Source: "dist\VideoSum\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; 配置文件
Source: "config\default_config.yaml"; DestDir: "{userappdata}\VideoSum"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// 检查Python是否安装
function IsPythonInstalled: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

// 检查FFmpeg是否安装
function IsFFmpegInstalled: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('ffmpeg', '-version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

// 安装前检查
function InitializeSetup: Boolean;
begin
  Result := True;
  
  if not IsPythonInstalled then
  begin
    if MsgBox('Python 3.10+ 未安装。是否继续安装？', mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
  end;
  
  if not IsFFmpegInstalled then
  begin
    MsgBox('FFmpeg 未安装。请在安装完成后手动安装FFmpeg。', mbInformation, MB_OK);
  end;
end;
