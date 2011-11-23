; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "Nemesys"
#define MyAppVersion "2.1"
#define MyAppPublisher "Fondazione Ugo Bordoni"
#define MyAppURL "http://www.misurainternet.it/"
#define MyAppExeName "Nemesys.exe"
#define MyAppDir "C:\Documents and Settings\Fondazione\Desktop\nemesys\trunk"

; Read the previuos build number. If there is none take 0 instead.
#define BuildNum Int(ReadIni(SourcePath	+ "\\buildinfo.ini","Info","Build","1"))
; Increment the build number by one.
#expr BuildNum = BuildNum + 1
; Store the number in the ini file for the next build
#expr WriteIni(SourcePath + "\\buildinfo.ini","Info","Build", BuildNum)

[Setup]
;AppId={21F1511D-B744-4DCE-AEAA-55E5C0668A35}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName=Nemesys
AllowNoIcons=true
InfoBeforeFile={#MyAppDir}\EULA
LicenseFile={#MyAppDir}\LICENSE
OutputDir={#MyAppDir}
OutputBaseFilename={#MyAppName}_v.{#myAppVersion}-{#BuildNum}
SolidCompression=true
VersionInfoCopyright=(c) 2010-2011 Fondazione Ugo Bordoni
PrivilegesRequired=admin
SetupIconFile={#MyAppDir}\nemesys.ico
WizardSmallImageFile={#MyAppDir}\nemesys_55.bmp
WizardImageFile={#MyAppDir}\nemesys_164.bmp
AppCopyright=Fondazione Ugo Bordoni
AlwaysRestart=true

[Messages]
italian.AdminPrivilegesRequired=Errore nell'installazione.%nSono necessarie le credenziali di amministratore per poter procedere.

[Languages]
Name: italian; MessagesFile: compiler:Languages\Italian.isl

[Tasks]
Name: quicklaunchicon; Description: {cm:CreateQuickLaunchIcon}; GroupDescription: {cm:AdditionalIcons}; Flags: unchecked; OnlyBelowVersion: 0,6.1

[Files]
Source: {#MyAppDir}\nemesys\winpcap\WinPcap.exe; Flags: dontcopy
Source: {#MyAppDir}\nemesys\dist\*; DestDir: {app}\dist; Flags: ignoreversion recursesubdirs createallsubdirs
Source: {#MyAppDir}\nemesys\cfg\*; DestDir: {app}\dist\cfg; Flags: ignoreversion recursesubdirs createallsubdirs
Source: {#MyAppDir}\ABOUT; DestDir: {app}; Flags: ignoreversion
Source: {#MyAppDir}\nemesys.ico; DestDir: {app}; Flags: ignoreversion
Source: {#MyAppDir}\COPYING; DestDir: {app}; Flags: ignoreversion
Source: {#MyAppDir}\LICENSE; DestDir: {app}; Flags: ignoreversion
Source: {#MyAppDir}\config\errorcodes.conf; DestDir: {app}\config; Flags: ignoreversion
Source: {#MyAppDir}\icons\*.png; DestDir: {app}\icons; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Dirs]
;Name: {app}\include
;Name: {app}\lib
Name: {app}\outbox
Name: {app}\sent
Name: {app}\logs

[Icons]
Name: {group}\Nemesys GUI; Filename: {app}\dist\gui.exe
Name: {group}\{cm:UninstallProgram,{#MyAppName}}; Filename: {uninstallexe}
Name: {commondesktop}\Nemesys GUI; Filename: {app}\dist\gui.exe; IconIndex: 0
Name: {userappdata}\Microsoft\Internet Explorer\Quick Launch\Nemesys GUI; Filename: {app}\dist\gui.exe; Tasks: quicklaunchicon; IconIndex: 0

[Run]
Filename: {app}\dist\Nemesys.exe; Parameters: --startup auto install; Description: Installazione del servizio Nemesys.; StatusMsg: Installazione del servizio Nemesys; Flags: runhidden RunAsCurrentUser
Filename: {app}\dist\Nemesys.exe; Parameters: start; Description: Avvia il servizio Nemesys.; Flags: postinstall runhidden RunAsCurrentUser; StatusMsg: Avvia il servizio Nemesys
;Filename: {app}\dist\gui.exe;Description: Avvia la GUI del servizio Nemesys.; Flags: postinstall nowait runhidden RunAsCurrentUser 

[UninstallRun]
Filename: taskkill; Parameters: /f /im gui.exe; WorkingDir: {sys}; Flags: runminimized RunAsCurrentUser
Filename: {app}\dist\Nemesys.exe; Parameters: " --wait 25 stop"; Flags: runminimized RunAsCurrentUser
Filename: {app}\dist\Nemesys.exe; Parameters: " remove"; Flags: runminimized RunAsCurrentUser

[UninstallDelete]
Type: files; Name: {app}\dist\cfg\*
Type: files; Name: {app}\dist\*
Type: files; Name: {app}\config\*
Type: files; Name: {app}\docs\*
Type: files; Name: {app}\icons\*
Type: files; Name: {app}\outbox\*
Type: files; Name: {app}\sent\*
Type: files; Name: {app}\logs\*
Type: dirifempty; Name: {app}\dist\cfg
Type: dirifempty; Name: {app}\dist
Type: dirifempty; Name: {app}\config
Type: dirifempty; Name: {app}\docs
Type: dirifempty; Name: {app}\icons
Type: dirifempty; Name: {app}\include
Type: dirifempty; Name: {app}\lib
Type: dirifempty; Name: {app}\outbox
Type: dirifempty; Name: {app}\sent
Type: dirifempty; Name: {app}\logs
Type: dirifempty; Name: {app}

[Registry]
root: HKLM; subkey: SYSTEM\CurrentControlSet\Services\Nemesys; valuetype: expandsz; valuename: ImagePath; valuedata: {app}; Flags: UninsDeleteKey DeleteKey
root: HKLM; subkey: SYSTEM\CurrentControlSet\Services\Nemesys; valuetype: multisz; valuename: DependOnService; valuedata: EventSystem{break}Tcpip{break}Netman{break}EventLog{break}; Flags: UninsDeleteKey DeleteKey
root: HKLM; subkey: SYSTEM\CurrentControlSet\Services\Nemesys; valuetype: binary; valuename: FailureActions; Flags: UninsDeleteKey DeleteKey; ValueData: 00 00 00 00 00 00 00 00 00 00 00 00 03 00 00 00 53 00 65 00 01 00 00 00 60 ea 00 00 01 00 00 00 60 ea 00 00 01 00 00 00 60 ea 00 00 
root: HKLM; subkey: SYSTEM\CurrentControlSet\Services\EventSystem; valuetype: dword; valuename: Start; valuedata: 2
root: HKLM; subkey: SYSTEM\CurrentControlSet\Services\Tcpip\Parameters; valuetype: dword; valuename: DisableTaskOffload; valuedata: 1; 

[Code]
procedure CancelButtonClick(CurPageID: Integer; var Cancel, Confirm: Boolean);
begin
  Cancel := true;
  Confirm := false;
end;

procedure WinPcapInst();
var
  ResultCode: Integer;
begin
  ExtractTemporaryFile(ExpandConstant('WinPcap.exe'));
  Exec(ExpandConstant('{tmp}\WinPcap.exe'),'', '', SW_SHOW,ewWaitUntilTerminated, ResultCode);
  if not RegValueExists(HKEY_LOCAL_MACHINE, 'SYSTEM\CurrentControlSet\Services\NPF','Start')
  then
    begin
      MsgBox('Installazione del software NeMeSys terminata poich� si � scelto di non installare WinPcap',mbInformation, MB_OK);
      WizardForm.Close;
    end
  else
    begin
      RegWriteDWordValue(HKEY_LOCAL_MACHINE, 'SYSTEM\CurrentControlSet\Services\NPF','Start', 2);
    end;
end;

procedure WinPcapRem();
var
  ResultCode: Integer;
  uninstallPath: String;
begin
  if RegValueExists(HKEY_LOCAL_MACHINE,'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\WinPcapInst','UninstallString')
  then
    begin
      RegQueryStringValue(HKEY_LOCAL_MACHINE,'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\WinPcapInst','UninstallString',uninstallPath);
      Exec(RemoveQuotes(uninstallPath),'', '', SW_SHOW,ewWaitUntilTerminated, ResultCode);
    end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall
  then 
    begin
      WinPcapInst();
    end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
    if CurUninstallStep = usPostUninstall
    then
      begin
        WinPcapRem();
      end;
end;

var
  WarningPage: TOutputMsgWizardPage;

procedure InitializeWizard;
begin

  WarningPage := CreateOutputMsgPage(wpInfoBefore,
    'Attenzione', 'Prima di continuare l''installazione...',
    '...controlla che tutto sia in ordine per l''esecuzione delle misure:'#13#13
    '1. Hai connesso il PC al modem via cavo?'#13#13 +
    '2. Hai chiuso tutte le applicazioni che accedono ad Internet? Per esempio:'#13 +
    '   * browser per la navigazione Internet'#13 +
    '   * programmi per l''accesso alla posta elettronica'#13 +
    '   * altri programmi come: Skype, MSN Messenger, Dropbox, ecc...'#13#13 +
    '3. Hai spento tutti i dispositivi che accedono ad Internet? Ad esempio:'#13 +
    '   * Console'#13 +
    '   * Smart-TV'#13 +
    '   * Smartphone'#13 +
    '   * IPTV'#13 +
    '   * VoIP'#13#13 +
    'Controlla di aver verificato che tutte le condizioni siano rispettate, poi procedi pure con l''installazione.');

end;

