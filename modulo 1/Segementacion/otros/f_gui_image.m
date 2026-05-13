function varargout = f_gui_image(varargin)
% F_GUI_IMAGE MATLAB code for f_gui_image.fig
%      F_GUI_IMAGE, by itself, creates a new F_GUI_IMAGE or raises the existing
%      singleton*.
%
%      H = F_GUI_IMAGE returns the handle to a new F_GUI_IMAGE or the handle to
%      the existing singleton*.
%
%      F_GUI_IMAGE('CALLBACK',hObject,eventData,handles,...) calls the local
%      function named CALLBACK in F_GUI_IMAGE.M with the given input arguments.
%
%      F_GUI_IMAGE('Property','Value',...) creates a new F_GUI_IMAGE or raises the
%      existing singleton*.  Starting from the left, property value pairs are
%      applied to the GUI before f_gui_image_OpeningFcn gets called.  An
%      unrecognized property name or invalid value makes property application
%      stop.  All inputs are passed to f_gui_image_OpeningFcn via varargin.
%
%      *See GUI Options on GUIDE's Tools menu.  Choose "GUI allows only one
%      instance to run (singleton)".
%
% See also: GUIDE, GUIDATA, GUIHANDLES

% Edit the above text to modify the response to help f_gui_image

% Last Modified by GUIDE v2.5 21-Apr-2014 10:31:31

% Begin initialization code - DO NOT EDIT
gui_Singleton = 1;
gui_State = struct('gui_Name',       mfilename, ...
                   'gui_Singleton',  gui_Singleton, ...
                   'gui_OpeningFcn', @f_gui_image_OpeningFcn, ...
                   'gui_OutputFcn',  @f_gui_image_OutputFcn, ...
                   'gui_LayoutFcn',  [] , ...
                   'gui_Callback',   []);
if nargin && ischar(varargin{1})
    gui_State.gui_Callback = str2func(varargin{1});
end

if nargout
    [varargout{1:nargout}] = gui_mainfcn(gui_State, varargin{:});
else
    gui_mainfcn(gui_State, varargin{:});
end
% End initialization code - DO NOT EDIT


% --- Executes just before f_gui_image is made visible.
function f_gui_image_OpeningFcn(hObject, eventdata, handles, varargin)
% This function has no output args, see OutputFcn.
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
% varargin   command line arguments to f_gui_image (see VARARGIN)

% Choose default command line output for f_gui_image
handles.output = hObject;

handles.output = hObject;
n=length(varargin);
if n>0
  handles.input.imagen=varargin{1,1};
  %handles.input.ScoutView=varargin{1,2};
  %handles.input.TIFF_DICOM=varargin{1,3};
  %handles.input.pixel_cm=varargin{1,4};
  %handles.input.Camera=varargin{1,5};
  %handles.input.nbeam=varargin{1,6};
  %handles.input.paciente=varargin{1,7};
end



% Update handles structure
guidata(hObject, handles);

% UIWAIT makes f_gui_image wait for user response (see UIRESUME)
% uiwait(handles.figure1);


% --- Outputs from this function are returned to the command line.
function varargout = f_gui_image_OutputFcn(hObject, eventdata, handles) 
% varargout  cell array for returning output args (see VARARGOUT);
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Get default command line output from handles structure
varargout{1} = handles.output;

I=handles.input.imagen;
n=size(I,3);
set(handles.tag_slice_bar,'Value',1) %primero hacer esto sino queda afuera del rango [0 1] 
set(handles.tag_slice_bar,'Min',1)
set(handles.tag_slice_bar,'Max',n)
%set(handles.tag_slice_bar,'SliderStep',[1 8]) 
set(handles.tag_nslice,'String','Slice number: 1');
% hay que modifica el tamaño del slice bar 

colormap(gray);
axes(handles.tag_axes1);
imshow(I(:,:,1),[]);
%freezeColors;

% --- Executes on slider movement.
function tag_slice_bar_Callback(~, eventdata, handles)
% hObject    handle to tag_slice_bar (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'Value') returns position of slider
%        get(hObject,'Min') and get(hObject,'Max') to determine range of slider

I=handles.input.imagen;

%selection=get(handles.funciones_graficas,'Value');
nslice=get(handles.tag_slice_bar,'Value')
nslice=round(nslice);

txt='Slice number: ';
txt=[txt,num2str(nslice)];
set(handles.tag_nslice,'String',txt);
imshow(I(:,:,nslice),[])


% --- Executes during object creation, after setting all properties.
function tag_slice_bar_CreateFcn(hObject, eventdata, handles)
% hObject    handle to tag_slice_bar (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: slider controls usually have a light gray background.
if isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor',[.9 .9 .9]);
end
