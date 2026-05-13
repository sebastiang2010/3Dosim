%%version 1.5 12/07/17

clc
close all
clear all 
%numero de visulizaciones <10000
disp(' ')
n=input(' Ingrese el numero de particulas (<1000): ');

%
fig=1; 

%%Hay que eliminar a mano las primeras columnas 
file=[];
[a,file]=f_cargo_ptract(file);




a2=zeros(10000,8);
n1=1;
for i=1:3:size(a,1); 
    a1=a(i,:);
    a2(n1,:)=a1(1,1:8);
    a1=[];
    n1=n1+1;
end
 
% 
pos=a2(:,1:3);

vec=a2(:,4:6); 

E=a2(:,7);

wgt=a2(:,8);


figure(fig)
fig=fig+1; 
scatter3([pos(:,1);pos(:,1)],[pos(:,2);pos(:,2)],[pos(:,3);pos(:,3)]);
xlabel('X')
ylabel('Y')
zlabel('Z')


figure(fig)
fig=fig+1; 
tic 
for i=1:n
    x=pos(i,1);
    y=pos(i,2);
    z=pos(i,3);
    x0=pos(i,1);
    y0=pos(i,2);
    z0=pos(i,3);
    h=scatter3([x0;x],[y0;y],[z0,z]);
    xlabel('X')
    ylabel('Y')
    zlabel('Z')
    hold on 
    c='b'; 
    %c=rand(1,3);
    %if E(i)==a(1);c='r';end 
    %if E(i)==a(2);c='g';end 
    %if E(i)==a(3);c='b';end 
    %if E(i)==a(4);c='y';end 
    set(h,'MarkerEdgeColor',c) 
    set(h,'SizeData',22)
    set(h,'MarkerFaceColor',c)
    pause(0.01)
end
time1=toc;

x0=0; 
y0=0; 
z0=0; 

x=1;
y=0;
z=0; 

% figure(fig)
% fig=fig+1;
% %grafico de verificacion 
% plot3([x0;x],[y0;y],[z0,z]);
% xlabel('X')
% hold on 
% x=0;
% y=1;
% z=0;
% h=plot3([x0;x],[y0;y],[z0,z]);
% set(h,'color','g') 
% ylabel('Y')
% x=0;
% y=0;
% z=1;
% h=plot3([x0;x],[y0;y],[z0,z]);
% set(h,'color','r') 
% xlabel('X')
% ylabel('Y')
% zlabel('Z')

%% grafico la fuente 
tic 
figure(fig)
fig=fig+1; 
for i=1:n
    x0=pos(i,1);
    y0=pos(i,2);
    z0=pos(i,3);
    %x0=0;
    %y0=0;
    %z0=0;
    x=x0+vec(i,1);
    y=y0+vec(i,2);
    z=z0+vec(i,3);
    h=plot3([x0;x],[y0;y],[z0;z]);
    c='g';
    % c=rand(1,3);
    %if E(i)==a(1);c='r';end 
    %if E(i)==a(2);c='g';end 
    %if E(i)==a(3);c='b';end 
    %if E(i)==a(4);c='y';end 
    set(h,'color',c) 
    hold on 
    h=scatter3([x0;x0],[y0;y0],[z0,z0]);
    c='b';
    set(h,'MarkerEdgeColor',c) 
    set(h,'SizeData',22)
    set(h,'MarkerFaceColor',c)
    xlabel('X')
    ylabel('Y')
    zlabel('Z')
    pause(0.01)
end
set(gca,'XGrid','on')
set(gca,'YGrid','on')
set(gca,'ZGrid','on')
time2=toc;


% figure(fig)
% fig=fig+1; 
% %grafico de verificacion 
% plot3([x0;x],[y0;y],[z0,z]);
% xlabel('X')
% hold on 
% x=0;
% y=1;
% z=0;
% h=plot3([x0;x],[y0;y],[z0,z]);
% set(h,'color','g') 
% ylabel('Y')
% x=0;
% y=0;
% z=1;
% h=plot3([x0;x],[y0;y],[z0,z]);
% set(h,'color','r') 
% xlabel('X')
% ylabel('Y')
% zlabel('Z')
% 
% %% grafico la fuente 
% tic 
% figure(fig)
% fig=fig+1;
% for i=1:n
%     x0=pos(i,1);
%     y0=pos(i,2);
%     z0=pos(i,3);
%     %x0=0;
%     %y0=0;
%     %z0=0;
%     x=x0+vec(i,1);
%     y=y0+vec(i,2);
%     z=z0+vec(i,3);
%     h=plot3([x0;x],[y0;y],[z0;z]);
%     %if E(i)==a(1);c='r';end 
%     %if E(i)==a(2);c='g';end 
%     %if E(i)==a(3);c='b';end 
%     %if E(i)==a(4);c='y';end 
%     set(h,'color',c) 
%     hold on 
%     h=scatter3([x;x],[y;y],[z,z]);
%     set(h,'MarkerEdgeColor',c) 
%     set(h,'SizeData',22)
%     set(h,'MarkerFaceColor',c)
%     xlabel('X')
%     ylabel('Y')
%     zlabel('Z')
%     pause(0.01)
% end

