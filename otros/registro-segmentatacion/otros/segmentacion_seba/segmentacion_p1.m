%% snakes
% sacado de crhts image
clear all
close all 
clc 

I=zeros(250,250); 
I(125:150,125:150)=1;

figure(1)
imshow(I,[]);
hold on 
%% genero el snake
xc=142; yc=142; r=30;               % Centro  y  radio
n = 50;  k=0:n;  fi=2*pi*k/n;
x=xc+r*cos(fi); y = yc+r*sin(fi);
plot(xc,yc,'x',x,y,'g');

%% generar la fuerza interna 
alpha=0.001;
beta=0.4;
gamma=100; 

%N=length(x); 
N=10; 
a=gamma*(2*alpha+6*beta)+1;
b=gamma*(-alpha-4*beta);
c=gamma*beta;
P=diag(repmat(a,1,N));
P=P+diag(repmat(b,1,N-1),1)+diag(b,-N+1);
P=P+diag(repmat(b,1,N-1),-1)+diag(b,N-1);
P=P+diag(repmat(c,1,N-2),2)+diag([c,c],-N+2);
P=P+diag(repmat(c,1,N-2),-2)+diag([c,c],N-2);

P=inv(P); 
%%
[FX, FY] = gradient(double(I));
h = fspecial('gaussian',30);
FY = imfilter(FY, h);
FX = imfilter(FX, h);
figure(2)
imshow(FX,[])
figure(3)
imshow(FY,[])

%% 
iterations=100;
for ii = 1:iterations
   % Calculate external force
   coords = [x,y];
   %fex = get_subpixel(f{1},coords,'linear');
   F = griddedInterpolant(FX,'linear');
   for i = 1:length(x)
       fex=F(x,y);
   end
   %fey = get_subpixel(f{2},coords,'linear');
   G = griddedInterpolant(FY,'linear');
   for i = 1:length(y)
       fey=G(x,y);
   end
      
   % Move control points
   x = P.*(x+gamma*fex);
   y = P.*(y+gamma*fey);
   if mod(ii,5)==0
      plot([x;x(1)],[y;y(1)],'b')
   end
end
plot([x;x(1)],[y;y(1)],'r')
