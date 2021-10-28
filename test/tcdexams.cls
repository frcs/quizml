\NeedsTeXFormat{LaTeX2e}[1994/06/01]
\ProvidesClass{tcdexams}[2021/02/25 v0.1 TCD EEE Exam Template]

\RequirePackage{fancyhdr} % headers and footers
\RequirePackage{lastpage} % for page reference in (1 of X)
\RequirePackage{mathptmx} % use Times for math mode
\RequirePackage{graphicx} % for logo

\renewcommand*{\familydefault}{\sfdefault} % Use default sans serif font

\DeclareOption{year}{\OptionNotUsed}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{\extarticle}}
\ProcessOptions\relax
\LoadClass[12pt,a4paper,oneside]{extarticle}


%% Toggles for the title page
\newif\if@instructions\@instructionsfalse
\newif\if@materials\@materialsfalse
\newif\if@additionalinformation\@additionalinformationfalse

%% Variables for the title page
\DeclareRobustCommand*{\faculty}[1]{\gdef\@faculty{#1}}
\DeclareRobustCommand*{\school}[1]{\gdef\@school{#1}}
\DeclareRobustCommand*{\department}[1]{\gdef\@department{#1}}
\DeclareRobustCommand*{\programmename}[1]{\gdef\@programmename{#1}}
\DeclareRobustCommand*{\programmeyearname}[1]{\gdef\@programmeyearname{#1}}
\DeclareRobustCommand*{\examsemester}[1]{\gdef\@examsemester{#1}}
\DeclareRobustCommand*{\examyear}[1]{\gdef\@examyear{#1}}
\DeclareRobustCommand*{\modulename}[1]{\gdef\@modulename{#1}}
\DeclareRobustCommand*{\modulecode}[1]{\gdef\@modulecode{#1}}
\DeclareRobustCommand*{\examdate}[1]{\gdef\@examdate{#1}}
\DeclareRobustCommand*{\examvenue}[1]{\gdef\@examvenue{#1}}
\DeclareRobustCommand*{\examtime}[1]{\gdef\@examtime{#1}}
\DeclareRobustCommand*{\examiner}[1]{\gdef\@examiner{#1}}
\DeclareRobustCommand{\instructions}[1]{\gdef\@instructions{#1}\@instructionstrue}
\DeclareRobustCommand{\materials}[1]{\gdef\@materials{#1}\@materialstrue}
\DeclareRobustCommand{\additionalinformation}[1]{\gdef\@additionalinformation{#1}\@additionalinformationtrue}

%% Defaults for the title page
\faculty{\textsc{\MakeUppercase{Faculty of Science, Technology, Engineering and Mathematics}}}
\school{\textsc{\MakeUppercase{School of Engineering}}}
\department{Electronic and Electrical Engineering}
\programmename{Engineering}

%% Set up page dimensions
\setlength{\hoffset}{-0.1in}
\setlength{\voffset}{-0.1in}
\setlength{\marginparwidth}{0mm}
\setlength{\marginparsep}{0mm}
\setlength{\headheight}{10mm}
\setlength{\headsep}{10mm}
\setlength{\footskip}{20mm}
\setlength{\oddsidemargin}{0mm}
\setlength{\evensidemargin}{0mm}
\setlength{\textwidth}{160mm}
\setlength{\textheight}{206mm}
\setlength{\topmargin}{0mm}

\setlength{\parindent}{0mm} % no indent for paragraphs

\linespread{1.3} % 1.5 linespacing

%% Redefine default page style
\fancypagestyle{plain}{%
	\fancyhf{}%
	\fancyhead[R]{\bfseries\protect\@modulecode}%
	\fancyfoot[C]{Page \textbf{\protect\thepage{}} of \textbf{\protect\pageref{LastPage}} \\ \bfseries\slshape\copyright{} Trinity College Dublin, The University of Dublin \protect\@examyear}%
	\renewcommand{\headrulewidth}{0mm}%
	\renewcommand{\footrulewidth}{0mm}%
}

%% Title Page
\renewenvironment{titlepage}{\@restonecolfalse\newpage}{\newpage}
\renewcommand*{\@maketitle}{
  \begin{titlepage}
    \bfseries
    \vspace*{-20mm}\hspace*{-10mm}\includegraphics[width=127mm]{tcdlogo} 
    \begin{center}
      \@faculty\par
      \@school\par
      \@department
    \end{center}

    {\@programmename \hfill \@examsemester, \@examyear}

    {\@programmeyearname}

    \begin{center}
      \@modulename
    \end{center}

    \@examdate \hfill \@examvenue \hfill \@examtime

    \begin{center}
      \@examiner
    \end{center}

    \if@instructions
      \par Instructions to candidates:\par
      \hspace*{0.05\textwidth}
      \begin{minipage}[t]{0.95\textwidth}
        \normalfont\@instructions
      \end{minipage}\par
      \vspace*{5mm}
    \fi

    \if@materials
    \par Materials Permitted for this Examination:\par
    \hspace*{0.05\textwidth}
    \begin{minipage}[t]{0.95\textwidth}
      \normalfont\@materials
    \end{minipage}\par
      \vspace*{5mm}
    \fi

    \if@additionalinformation
    \par Additional information:\par
    \hspace*{0.05\textwidth}
    \begin{minipage}[t]{0.95\textwidth}
      \normalfont\@additionalinformation
    \end{minipage}\par
      \vspace*{5mm}
    \fi
\end{titlepage}}
