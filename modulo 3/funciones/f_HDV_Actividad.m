function f_HDV_Actividad(A,I1,organo,nfig)

         %t_voxel cm          
         %organo=index.liver; 
         
         if organo==30;txt='Tejido Blando';end
         if organo==50;txt='Pulmon';end
         if organo==80;txt='Hueso';end
         if organo==90;txt='Higado sano';c='b';end    
         if organo>=100;txt='Tumor';c='r';end
         if organo==99;txt='Pretumor';c='g';end
         
                  
         A=double(A); 
         ind=I1==organo;
         A=A(ind);
         n=numel(A); %numero de pixel
         
         %Volumen=n*prod(tvoxel); %cm
         
         
         
         %%%%%histograma dosis Volumen
         Amax=max(A(:));
         delta=Amax/1000;
         i=1;
         a=zeros(1001,1);
         inicio=1; 
         for d=inicio:delta:Amax-delta
             a(i,1)=sum(A>=d)*100/n;
             i=i+1;
         end
         
         d=inicio:delta:Amax+delta;
         figure(nfig)
         %h_plot=plot(d',a(1:end-1));
         d=d'; 
         h_plot=plot(d,a(1:size(d,1)));
         
         set(h_plot,'LineWidth',2);
         set(h_plot,'Color',c)
         set(gca,'YLim',[0 max(a(:))+10]);
         set(gca,'XLim',[0 Amax+Amax*0.1]);
         h_x=xlabel(' uSphere ' );
         h_y=ylabel('Volume (%)');
         %h_title=title(['Cumulative uSphere Volume Histogram, uSphere: ',]);
         %set(h_title,'FontWeight','bold')
         set(h_x,'FontWeight','bold')
         set(h_y,'FontWeight','bold')
         set(gca,'XGrid','on')
         set(gca,'YGrid','on')
         set(gca,'XScale','log')
         %set(gca,'YLim',[0 110])
         
         txt={'Higado','pretumor','tumor'}; 
         legend(txt)
         %      Dmean=mean(D);
         %      sigma=std(D);
         %      Dmin=min(D);
end

