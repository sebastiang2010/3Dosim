function tally_ver=f_genero_tally(archivo,tvoxel,image_size,cell,max_e,tmesh)


fid=fopen(archivo, 'a+'); %agregar datos al archivo

clc 
parar=1;
n=1; 
while parar==1;
  clc 
  disp(' ')
  parar1=1;
  while parar1==1
      x(n)=input(' Ingrese la posicion X (MATLAB) del tally de verificacion:  ');
      if x(n)<1 || x(n)>image_size(1);
          disp(' ')
          disp(' Posicion de X no valida');
      else
          parar1=-1;
      end
  end
  
  disp('  ')
  parar1=1;
  while parar1==1
  y(n)=input(' Ingrese la posicion Y (MATLAB) del tally de verificacion:  ');
      if y(n)<1 || y(n)>image_size(2);
          disp(' ')
          disp(' Posicion de Y no valida');
      else
          parar1=-1;
      end
  end
  
  disp('  ')
  parar1=1;
  while parar1==1
  z(n)=input(' Ingrese la posicion Z (MATLAB) del tally de verificacion:  ');
      if z(n)<1 || z(n)>image_size(3);
          disp(' ')
          disp(' Posicion de z no valida');
      else
          parar1=-1;
      end
  end
  
  
  clc 
  disp('   ')
  a=input('  Desea ingresar otro tally de verficacion (~=0-SI // 0=NO):  ');
  if a==0;parar=-1;end
  n=n+1; 
end

tally_ver=[x; y; z];

x1=x-1;
y1=y; 
z1=z-1;

y1=(image_size(2)-y1); %por que esta flipeado


b(1)=image_size(1)*tvoxel(1);
b(2)=image_size(2)*tvoxel(2);
b(3)=image_size(3)*tvoxel(3);

a=b./tvoxel; % numero de separaciones para generar el tally  
a=a-1; 

if tmesh(1)==1; %tally 1
    fprintf(fid,' \n');
    fprintf(fid,'c \n');
    fprintf(fid,'c TALLY \n');
    fprintf(fid,'c MESH TALLY 1=F6 \n');
    fprintf(fid,'c MeV/(cm^3 source_particle)  \n');
    fprintf(fid,'tmesh \n');
    fprintf(fid,'c \n');
    fprintf(fid,'rmesh1:e   pedep \n');
    fprintf(fid,'cora1  0');
    fprintf(fid,'  %g',a(1));
    fprintf(fid,'i');
    fprintf(fid,'   %g \n',b(1));
    fprintf(fid,'corb1  0');
    fprintf(fid,'  %g',a(2));
    fprintf(fid,'i');
    fprintf(fid,'   %g \n',b(2));
    fprintf(fid,'corc1  0');
    fprintf(fid,'  %g',a(3));
    fprintf(fid,'i');
    fprintf(fid,'   %g \n',b(3));
end
if tmesh(2)==1;
    fprintf(fid,'c  \n');
    fprintf(fid,'c MESH TALLY 3=+F6 \n');
    fprintf(fid,'c MeV/(cm^3 source_particle)  \n');
    fprintf(fid,'rmesh3 total \n');
    fprintf(fid,'cora3  0');
    fprintf(fid,'  %g',a(1));
    fprintf(fid,'i');
    fprintf(fid,'   %g \n',b(1));
    fprintf(fid,'corb3  0');
    fprintf(fid,'  %g',a(2));
    fprintf(fid,'i');
    fprintf(fid,'   %g \n',b(2));
    fprintf(fid,'corc3  0');
    fprintf(fid,'  %g',a(3));
    fprintf(fid,'i');
    fprintf(fid,'   %g \n',b(3));
    fprintf(fid,'c \n');
end
% fin del mesh tally
fprintf(fid,'endmd \n');
fprintf(fid,'c \n');
if tmesh(1)==1;
    fprintf(fid,'ergsh1  0  1e-5');
    fprintf(fid,'  %g',max_e);
    fprintf(fid,' \n');
end
if tmesh(2)==1;
    fprintf(fid,'ergsh3  0  1e-5');
    fprintf(fid,'  %g',max_e);
    fprintf(fid,' \n');
end
fprintf(fid,'c  \n');
n=length(cell);
for i=1:length(x);
    fprintf(fid,'c Tally de verificacion \n');
    a=['c *f',num2str(i),'8  MeV \n'];
    fprintf(fid,a);
    fprintf(fid,'c Posicion MATLAB ');
    fprintf(fid,' [%g',x(i));
    fprintf(fid,' %g',y(i) );
    fprintf(fid,' %g] \n',z(i));
    a=['*f',num2str(i),'8:p,e'];
    %fprintf(fid,'*f8:p,e  ');
    fprintf(fid,a);
    fprintf(fid,' (%g',max(cell)+1);
%     if op_fuente==3
%         fprintf(fid,' <%g',max(cell)+1);
%     else
    fprintf(fid,' <%g',max(cell)+2);
%     end
    fprintf(fid,' [%g',x1(i));
    fprintf(fid,' %g',y1(i));
    fprintf(fid,' %g]',z1(i));
    fprintf(fid,') \n');
end
fclose(fid);

end