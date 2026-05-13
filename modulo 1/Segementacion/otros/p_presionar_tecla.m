% 
% f = warndlg('This is a warning.', 'A Warning Dialog');
% disp('This prints immediately');
% drawnow     % Necessary to print the message
% waitfor(f);
% disp('This prints after you close the warning dialog');
f = figure('Name', datestr(now));
h = uicontrol('String', 'Change Name', 'Position', [20 20 100 30], ...
'Callback', 'set(gcbf, ''Name'', datestr(now))');
disp('This prints immediately');
drawnow     % Necessary to print the message
waitfor(f, 'Name');
disp('This prints after button click that changes the figure''s name');



% w = waitforbuttonpress;
% if w == 0
%     disp('Button click')
% else
%     disp('Key press')
% end




% clc 
% parar=1;
% x1=1;
% while parar==1
% 
%     clc
% key=input(' Ingrese ENTER para incrementar ');
% 
% if isempty(key);
%     x1=x1+1;
% else
%     parar=-1;
%     
% end
% end 


% t = 0:pi/20:2*pi;
% y = exp(sin(t));
% h = plot(t,y,'YDataSource','y');
% for k = 1:.1:10
% 	y = exp(sin(t.*k));
% 	refreshdata(h,'caller') % Evaluate y in the function workspace
% 	drawnow; pause(.1)
% end

% t=cputime;
% e=cputime-t;
% tiempo=10;
% keypress=0; 
% while e<tiempo 
%        e=cputime-t 
%        [x,y,button]=ginput
%        if button=3;break;
%            
%        
%end     

% parar=1; 
% while parar~=1;
%       while ~waitforbuttonpress
%             para
%       end
%     
% end